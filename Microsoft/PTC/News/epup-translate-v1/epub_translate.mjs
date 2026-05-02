// epub-translate-v1 — EPUB translator (Node + epub.js + JSZip + cheerio)
//
// Pipeline: EXTRACT (epub.js spine 순회 + cheerio DOM walk)
//           → TRANSLATE (TM + 파일별 dict.json 누적 + LLM batch)
//           → APPLY    (원본 EPUB 복사 → JSZip + cheerio 로 텍스트 노드 in-place 치환)
//
// 입력 원본은 변경하지 않는다. DRM/암호화로 XHTML 을 읽지 못하면 해당 파일은 skip.

import 'dotenv/config';
import fs from 'node:fs';
import fsp from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { Command } from 'commander';
import pc from 'picocolors';
import JSZip from 'jszip';
import * as cheerio from 'cheerio';
import Database from 'better-sqlite3';
import OpenAI from 'openai';
import { JSDOM } from 'jsdom';

// ────────────────────────────────────────────────
// epub.js 가 Node 에서 동작하도록 DOM 글로벌 주입
// ────────────────────────────────────────────────
const _dom = new JSDOM('<!doctype html><html><head></head><body></body></html>', {
    url: 'http://localhost/',
});
for (const k of ['window', 'document', 'DOMParser', 'XMLSerializer', 'Node', 'Element', 'Blob']) {
    if (globalThis[k] === undefined && _dom.window[k] !== undefined) {
        globalThis[k] = _dom.window[k];
    }
}
const ePub = (await import('epubjs')).default;

// ────────────────────────────────────────────────
// 설정
// ────────────────────────────────────────────────
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const settings = {
    openaiApiKey: process.env.OPENAI_API_KEY || '',
    openaiModel: process.env.OPENAI_MODEL || 'gpt-4o-mini',
    azureApiKey: process.env.AZURE_OPENAI_API_KEY || '',
    azureEndpoint: process.env.AZURE_OPENAI_ENDPOINT || '',
    azureApiVersion: process.env.AZURE_OPENAI_API_VERSION || '2024-08-01-preview',
    azureDeployment: process.env.AZURE_OPENAI_DEPLOYMENT || '',
    sourceLang: (process.env.SOURCE_LANG || 'en').toLowerCase(),
    targetLang: (process.env.TARGET_LANG || 'kr').toLowerCase(),
    workDir: process.env.WORK_DIR || 'work',
    tmDbPath: process.env.TM_DB_PATH || 'work/tm.sqlite',
    glossaryPath: process.env.GLOSSARY_PATH || 'glossary.csv',
    krFont: process.env.KR_FONT || '맑은 고딕',
};

const LANG_NAMES = { en: 'English', kr: 'Korean', jp: 'Japanese', ch: 'Chinese' };
const LANG_LABELS = { en: 'EN', kr: 'KR', jp: 'JP', ch: 'CH' };

function llmModel() {
    return settings.azureDeployment ? `azure/${settings.azureDeployment}` : settings.openaiModel;
}

// ────────────────────────────────────────────────
// 로그
// ────────────────────────────────────────────────
const log = {
    info: (m) => console.log(m),
    step: (m) => console.log(pc.bold(m)),
    warn: (m) => console.log(pc.yellow(m)),
    err: (m) => console.log(pc.red(m)),
    ok: (m) => console.log(pc.green(m)),
    dim: (m) => console.log(pc.cyan(m)),
};

// ────────────────────────────────────────────────
// glossary.csv
// ────────────────────────────────────────────────
function loadGlossary() {
    const p = path.resolve(settings.glossaryPath);
    if (!fs.existsSync(p)) return {};
    const txt = fs.readFileSync(p, 'utf8');
    const lines = txt.split(/\r?\n/).filter(Boolean);
    const header = lines.shift().split(',');
    const idx = (k) => header.indexOf(k);
    const out = {};
    for (const line of lines) {
        const cells = parseCsvLine(line);
        const term = (cells[idx('term')] || '').trim();
        if (!term) continue;
        out[term] = {
            translation: (cells[idx('translation')] || '').trim(),
            protected: ['1', 'true', 'yes'].includes((cells[idx('protected')] || '').trim().toLowerCase()),
        };
    }
    return out;
}

function parseCsvLine(line) {
    const out = [];
    let cur = '';
    let inQ = false;
    for (let i = 0; i < line.length; i++) {
        const c = line[i];
        if (inQ) {
            if (c === '"' && line[i + 1] === '"') { cur += '"'; i++; }
            else if (c === '"') inQ = false;
            else cur += c;
        } else {
            if (c === ',') { out.push(cur); cur = ''; }
            else if (c === '"') inQ = true;
            else cur += c;
        }
    }
    out.push(cur);
    return out;
}

// ────────────────────────────────────────────────
// TM (SQLite)
// ────────────────────────────────────────────────
function sha256(s) { return crypto.createHash('sha256').update(s, 'utf8').digest('hex'); }

function tmConnect() {
    const p = path.resolve(settings.tmDbPath);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    const db = new Database(p);
    db.exec(`CREATE TABLE IF NOT EXISTS tm (
    src_hash TEXT PRIMARY KEY,
    src TEXT NOT NULL,
    tgt TEXT NOT NULL,
    model TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  )`);
    return db;
}

function tmLookup(db, src) {
    const row = db.prepare('SELECT tgt FROM tm WHERE src_hash=?').get(sha256(src));
    return row ? row.tgt : null;
}

function tmStore(db, src, tgt, model) {
    db.prepare('INSERT OR IGNORE INTO tm (src_hash, src, tgt, model) VALUES (?, ?, ?, ?)')
        .run(sha256(src), src, tgt, model || '');
}

// ────────────────────────────────────────────────
// LLM 클라이언트
// ────────────────────────────────────────────────
function makeLlmClient() {
    if (settings.azureDeployment && settings.azureApiKey && settings.azureEndpoint) {
        return new OpenAI({
            apiKey: settings.azureApiKey,
            baseURL: `${settings.azureEndpoint.replace(/\/+$/, '')}/openai/deployments/${settings.azureDeployment}`,
            defaultQuery: { 'api-version': settings.azureApiVersion },
            defaultHeaders: { 'api-key': settings.azureApiKey },
        });
    }
    if (!settings.openaiApiKey) throw new Error('OPENAI_API_KEY 또는 AZURE_OPENAI_* 가 .env 에 설정되어야 합니다');
    return new OpenAI({ apiKey: settings.openaiApiKey });
}

function llmCallModel() {
    return settings.azureDeployment ? settings.azureDeployment : settings.openaiModel;
}

// ────────────────────────────────────────────────
// EPUB 열기 (epub.js + JSZip 동시 보유)
// ────────────────────────────────────────────────
async function openEpub(epubPath) {
    const buf = await fsp.readFile(epubPath);
    const zip = await JSZip.loadAsync(buf);

    // 암호화 검사 — META-INF/encryption.xml 존재 시 DRM 가능성
    if (zip.file('META-INF/encryption.xml')) {
        log.warn(`  [DRM] META-INF/encryption.xml 감지: ${path.basename(epubPath)} → 스킵`);
        return null;
    }

    // epub.js: ArrayBuffer 입력
    const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
    const book = ePub(ab);
    try {
        await book.opened;
    } catch (e) {
        log.warn(`  [parse fail] epub.js opened 실패: ${e.message} → 스킵`);
        return null;
    }
    return { book, zip, buf };
}

function spineHrefs(book) {
    // book.spine.items[].href 는 OPF 기준 상대경로. zip 내 절대경로로 변환.
    const opfPath = book.packaging?.packagingPath || book.spine?.packagingPath || '';
    const opfDir = opfPath ? path.posix.dirname(opfPath) : '';
    const out = [];
    for (const it of book.spine.items) {
        if (!it.href) continue;
        const href = decodeURIComponent(it.href.split('#')[0]);
        const full = opfDir ? path.posix.join(opfDir, href) : href;
        out.push({ idref: it.idref, href: full, raw: it.href });
    }
    return out;
}

// ────────────────────────────────────────────────
// DOM walk: 텍스트 노드 path 수집
// path = [child_idx, child_idx, ...] (root html 원소부터 텍스트 노드까지)
// ────────────────────────────────────────────────
const SKIP_TAGS = new Set(['script', 'style', 'code', 'pre', 'kbd', 'samp', 'tt']);

function isTranslatableText(s) {
    if (!s) return false;
    const t = s.trim();
    if (t.length === 0) return false;
    // 숫자/기호만
    if (!/[A-Za-z\u00C0-\u024F\u0370-\u03FF\u0400-\u04FF\u4E00-\u9FFF\uAC00-\uD7A3\u3040-\u30FF]/.test(t)) return false;
    // URL/email
    if (/^https?:\/\/\S+$/i.test(t)) return false;
    if (/^[\w.+-]+@[\w.-]+\.\w+$/i.test(t)) return false;
    return true;
}

function inferKind(parents) {
    for (const tag of parents) {
        if (/^h[1-6]$/i.test(tag)) return tag.toLowerCase();
        if (tag === 'li') return 'li';
        if (tag === 'figcaption') return 'figcaption';
        if (tag === 'blockquote') return 'blockquote';
        if (tag === 'p') return 'p';
    }
    return 'text';
}

function walkXhtml(xhtmlText, hrefForLog) {
    let $;
    try {
        $ = cheerio.load(xhtmlText, { xmlMode: true, decodeEntities: false });
    } catch (e) {
        log.warn(`  [parse fail] ${hrefForLog}: ${e.message}`);
        return [];
    }
    const root = $.root()[0];
    const segments = [];
    const stack = []; // tag stack for kind detection

    function visit(node, pathArr) {
        if (node.type === 'tag') {
            const name = (node.name || '').toLowerCase();
            if (SKIP_TAGS.has(name)) return;
            stack.push(name);
            const children = node.children || [];
            for (let i = 0; i < children.length; i++) {
                visit(children[i], pathArr.concat(i));
            }
            stack.pop();
        } else if (node.type === 'text') {
            const data = node.data || '';
            if (isTranslatableText(data)) {
                segments.push({
                    path: pathArr,
                    text: data,
                    kind: inferKind([...stack].reverse()),
                });
            }
        }
        // comment / cdata 등은 무시
    }

    const top = root.children || [];
    for (let i = 0; i < top.length; i++) {
        visit(top[i], [i]);
    }
    return segments;
}

function applyToXhtml(xhtmlText, edits) {
    // edits: [{path, text}]
    const $ = cheerio.load(xhtmlText, { xmlMode: true, decodeEntities: false });
    const root = $.root()[0];

    function nodeAt(p) {
        let n = root;
        for (const idx of p) {
            if (!n.children || idx >= n.children.length) return null;
            n = n.children[idx];
        }
        return n;
    }

    let applied = 0;
    for (const ed of edits) {
        const n = nodeAt(ed.path);
        if (!n || n.type !== 'text') continue;
        n.data = ed.text;
        applied++;
    }
    return { xml: $.xml(), applied };
}

// ────────────────────────────────────────────────
// EXTRACT
// ────────────────────────────────────────────────
async function extract(epubPath) {
    const opened = await openEpub(epubPath);
    if (!opened) return null;
    const { book, zip } = opened;

    const segments = [];
    const spine = spineHrefs(book);
    log.dim(`  spine ${spine.length}건`);

    for (let si = 0; si < spine.length; si++) {
        const s = spine[si];
        const f = zip.file(s.href);
        if (!f) {
            log.warn(`  [missing] ${s.href} → 스킵`);
            continue;
        }
        let xml;
        try {
            xml = await f.async('string');
        } catch (e) {
            log.warn(`  [read fail] ${s.href}: ${e.message} → 스킵`);
            continue;
        }
        const segs = walkXhtml(xml, s.href);
        for (const seg of segs) {
            segments.push({
                spine: si,
                href: s.href,
                path: seg.path,
                text: seg.text,
                kind: seg.kind,
            });
        }
    }

    // 메타데이터: dc:title (옵션)
    return {
        metadata: {
            title: book.packaging?.metadata?.title || '',
            language: book.packaging?.metadata?.language || '',
        },
        spine,
        segments,
    };
}

// ────────────────────────────────────────────────
// TRANSLATE
// ────────────────────────────────────────────────
const BATCH_SIZE = 10;

async function translateSegments(segments, workDir) {
    const db = tmConnect();
    const glossary = loadGlossary();
    const client = makeLlmClient();

    // 파일별 dict.json (proper noun 누적)
    const dictPath = path.join(workDir, 'dict.json');
    /** @type {Record<string,string>} */
    let fileDict = {};
    if (fs.existsSync(dictPath)) {
        try { fileDict = JSON.parse(fs.readFileSync(dictPath, 'utf8')); } catch { fileDict = {}; }
    }

    const results = new Array(segments.length);
    const pending = []; // {idx, seg}

    for (let i = 0; i < segments.length; i++) {
        const seg = segments[i];
        const cached = tmLookup(db, seg.text);
        if (cached !== null) {
            results[i] = { ...seg, translated: cached };
        } else {
            pending.push({ idx: i, seg });
        }
    }

    log.dim(`  TM hit ${segments.length - pending.length}/${segments.length}, 미스 ${pending.length}`);

    for (let i = 0; i < pending.length; i += BATCH_SIZE) {
        const batch = pending.slice(i, i + BATCH_SIZE);
        const inputs = batch.map((b) => b.seg.text);

        const { translations, properNouns } = await translateBatchWithRetry(
            client, inputs, glossary, fileDict
        );

        // dict 누적
        for (const pn of properNouns || []) {
            if (pn.src && pn.tgt && !fileDict[pn.src]) fileDict[pn.src] = pn.tgt;
        }
        fs.writeFileSync(dictPath, JSON.stringify(fileDict, null, 2), 'utf8');

        for (let j = 0; j < batch.length; j++) {
            const tgt = translations[j];
            const seg = batch[j].seg;
            tmStore(db, seg.text, tgt, llmModel());
            results[batch[j].idx] = { ...seg, translated: tgt };
        }
        log.dim(`  ${Math.min(i + BATCH_SIZE, pending.length)}/${pending.length}`);
    }

    db.close();
    return results;
}

async function translateBatchWithRetry(client, inputs, glossary, fileDict) {
    try {
        return await callLlm(client, inputs, glossary, fileDict);
    } catch (e) {
        if (inputs.length === 1) {
            log.warn(`  번역 실패, 원문 유지: ${inputs[0].slice(0, 60)}... (${e.message})`);
            return { translations: [inputs[0]], properNouns: [] };
        }
        const mid = Math.floor(inputs.length / 2);
        const left = await translateBatchWithRetry(client, inputs.slice(0, mid), glossary, fileDict);
        const right = await translateBatchWithRetry(client, inputs.slice(mid), glossary, fileDict);
        return {
            translations: [...left.translations, ...right.translations],
            properNouns: [...(left.properNouns || []), ...(right.properNouns || [])],
        };
    }
}

async function callLlm(client, inputs, glossary, fileDict) {
    const srcName = LANG_NAMES[settings.sourceLang] || settings.sourceLang;
    const tgtName = LANG_NAMES[settings.targetLang] || settings.targetLang;

    const glossaryLines = Object.entries(glossary).map(
        ([t, v]) => `- ${t}: ${v.translation}${v.protected ? ' (protected)' : ''}`
    );
    const dictLines = Object.entries(fileDict).map(([s, t]) => `- ${s}: ${t}`);

    const system = [
        `You translate ${srcName} to ${tgtName}.`,
        'Input is a JSON array of plain strings (each = one inline text node from EPUB XHTML).',
        'Return ONLY a JSON object: {"translations": ["..."], "proper_nouns": [{"src":"...","tgt":"..."}]}',
        'translations: same length and order as input. Each element is the translated string only — no JSON, no brackets, no English mixed in.',
        'proper_nouns: proper nouns (people, products, organizations, places, technical terms) you encountered in this batch and their target-language form. Used to keep terminology consistent across the file.',
        'Do not translate (protected) terms. Keep numbers, URLs, code, citations, file paths unchanged. Preserve leading/trailing whitespace exactly.',
        'Glossary (highest priority):',
        glossaryLines.length ? glossaryLines.join('\n') : '(none)',
        'File dictionary (already-decided terms in this file):',
        dictLines.length ? dictLines.join('\n') : '(none)',
    ].join('\n');

    const user = JSON.stringify(inputs);

    const resp = await client.chat.completions.create({
        model: llmCallModel(),
        messages: [
            { role: 'system', content: system },
            { role: 'user', content: user },
        ],
        response_format: { type: 'json_object' },
        temperature: 0,
        max_tokens: 4096,
    });

    const content = resp.choices[0].message.content || '';
    const parsed = JSON.parse(content);

    let translations = parsed.translations;
    if (!Array.isArray(translations) || translations.length !== inputs.length) {
        throw new Error(`LLM 응답 길이 불일치 (expected=${inputs.length}, got=${Array.isArray(translations) ? translations.length : typeof translations})`);
    }
    translations = translations.map((x) => String(x));

    const properNouns = Array.isArray(parsed.proper_nouns)
        ? parsed.proper_nouns.filter((p) => p && typeof p.src === 'string' && typeof p.tgt === 'string')
        : [];

    return { translations, properNouns };
}

// ────────────────────────────────────────────────
// APPLY
// ────────────────────────────────────────────────
async function applyEpub(srcPath, translated, outPath) {
    await fsp.mkdir(path.dirname(outPath), { recursive: true });

    const buf = await fsp.readFile(srcPath);
    const zip = await JSZip.loadAsync(buf);

    // href → edits
    const byHref = new Map();
    for (const seg of translated) {
        if (!byHref.has(seg.href)) byHref.set(seg.href, []);
        byHref.get(seg.href).push({ path: seg.path, text: seg.translated });
    }

    let totalApplied = 0;
    for (const [href, edits] of byHref.entries()) {
        const f = zip.file(href);
        if (!f) {
            log.warn(`  [apply skip] ${href} 누락`);
            continue;
        }
        const xml = await f.async('string');
        const { xml: out, applied } = applyToXhtml(xml, edits);
        zip.file(href, out);
        totalApplied += applied;
    }

    // dc:language 갱신 (content.opf)
    const opfPath = findOpfPath(zip);
    if (opfPath) {
        const opfXml = await zip.file(opfPath).async('string');
        const $ = cheerio.load(opfXml, { xmlMode: true, decodeEntities: false });
        const lang = $('dc\\:language, language');
        if (lang.length) lang.first().text(targetLangBcp47());
        zip.file(opfPath, $.xml());
    }

    // 재압축. mimetype 은 STORE 로 first entry
    await writeEpubZip(zip, outPath);
    log.ok(`  적용 완료: ${outPath} (${totalApplied}건)`);
}

function targetLangBcp47() {
    const map = { kr: 'ko', en: 'en', jp: 'ja', ch: 'zh' };
    return map[settings.targetLang] || settings.targetLang;
}

function findOpfPath(zip) {
    const containerFile = zip.file('META-INF/container.xml');
    if (!containerFile) return null;
    // 동기 접근이 안 되니 caller 쪽에서 await 하지만 여기는 sync 인터페이스가 필요해 우회
    // 간단히: zip 내에서 .opf 확장자 첫 파일을 사용
    const files = Object.keys(zip.files).filter((n) => n.toLowerCase().endsWith('.opf'));
    return files[0] || null;
}

async function writeEpubZip(zip, outPath) {
    // mimetype 을 STORE 로 다시 추가
    const mt = zip.file('mimetype');
    let mimetypeContent = 'application/epub+zip';
    if (mt) mimetypeContent = await mt.async('string');
    // JSZip 은 동일 파일명 재추가 시 새 옵션으로 덮어쓴다
    zip.file('mimetype', mimetypeContent, { compression: 'STORE' });

    const out = await zip.generateAsync({
        type: 'nodebuffer',
        mimeType: 'application/epub+zip',
        compression: 'DEFLATE',
        compressionOptions: { level: 6 },
    });
    await fsp.writeFile(outPath, out);
}

// ────────────────────────────────────────────────
// 파일 단위 실행
// ────────────────────────────────────────────────
function workDirFor(epubPath) {
    const stem = path.basename(epubPath, path.extname(epubPath));
    const w = path.resolve(settings.workDir, stem);
    fs.mkdirSync(w, { recursive: true });
    return w;
}

function defaultOutPath(epubPath) {
    const stem = path.basename(epubPath, path.extname(epubPath));
    const ext = path.extname(epubPath);
    const parent = path.dirname(path.resolve(epubPath));
    const outDir = path.basename(parent).toLowerCase() === 'input'
        ? path.join(path.dirname(parent), 'output')
        : parent;
    fs.mkdirSync(outDir, { recursive: true });
    return path.join(outDir, `${stem}_${LANG_LABELS[settings.targetLang] || settings.targetLang.toUpperCase()}${ext}`);
}

function moveToDone(epubPath) {
    const src = path.resolve(epubPath);
    const doneDir = path.join(path.dirname(src), 'done');
    fs.mkdirSync(doneDir, { recursive: true });
    let dst = path.join(doneDir, path.basename(src));
    if (fs.existsSync(dst)) {
        const stem = path.basename(src, path.extname(src));
        const ext = path.extname(src);
        const ts = Math.floor(fs.statSync(src).mtimeMs / 1000);
        dst = path.join(doneDir, `${stem}_${ts}${ext}`);
    }
    fs.renameSync(src, dst);
    return dst;
}

async function runOne(epubPath, { output, moveDone } = {}) {
    const work = workDirFor(epubPath);
    const out = output || defaultOutPath(epubPath);

    log.step('EXTRACT');
    const extracted = await extract(epubPath);
    if (!extracted) {
        log.warn(`스킵: ${epubPath}`);
        return false;
    }
    fs.writeFileSync(path.join(work, 'segments.json'), JSON.stringify(extracted, null, 2), 'utf8');
    log.dim(`  세그먼트 ${extracted.segments.length}건`);

    log.step('TRANSLATE');
    const translated = await translateSegments(extracted.segments, work);
    fs.writeFileSync(path.join(work, 'translated.json'), JSON.stringify(translated, null, 2), 'utf8');

    log.step('APPLY');
    await applyEpub(epubPath, translated, out);

    if (moveDone) {
        const parent = path.basename(path.dirname(path.resolve(epubPath))).toLowerCase();
        if (parent === 'input') {
            const moved = moveToDone(epubPath);
            log.dim(`  done 이동: ${moved}`);
        }
    }
    return true;
}

function collectInputFiles(dir) {
    const out = [];
    for (const name of fs.readdirSync(dir).sort()) {
        const full = path.join(dir, name);
        if (!fs.statSync(full).isFile()) continue;
        if (!/\.epub$/i.test(name)) continue;
        out.push(full);
    }
    return out;
}

async function runDirectory(dir, opts) {
    const files = collectInputFiles(dir);
    if (files.length === 0) {
        log.warn(`대상 파일 없음: ${dir}`);
        return;
    }
    log.info(pc.bold(pc.cyan(`배치 실행: ${files.length}건`)));
    let ok = 0;
    const failed = [];
    for (let i = 0; i < files.length; i++) {
        const f = files[i];
        log.info(pc.bold(`──── [${i + 1}/${files.length}] ${path.basename(f)} ────`));
        try {
            const success = await runOne(f, opts);
            if (success) ok++;
        } catch (e) {
            log.err(`실패: ${path.basename(f)} (${e.message})`);
            failed.push([f, e.message]);
        }
    }
    log.info(pc.bold('──── 배치 종료 ────'));
    log.ok(`성공 ${ok}/${files.length}`);
    if (failed.length) {
        log.err(`실패 ${failed.length}건`);
        for (const [f, m] of failed) log.err(`  - ${path.basename(f)}: ${m}`);
    }
}

// ────────────────────────────────────────────────
// CLI
// ────────────────────────────────────────────────
const program = new Command();
program
    .name('epub_translate')
    .description('EPUB 번역 (epub.js + JSZip + cheerio)')
    .option('--in-lang <lang>', 'source language (en/kr/jp/ch)')
    .option('--out-lang <lang>', 'target language (en/kr/jp/ch)');

function applyLangOpts(opts) {
    if (opts.inLang) settings.sourceLang = opts.inLang.toLowerCase();
    if (opts.outLang) settings.targetLang = opts.outLang.toLowerCase();
}

program
    .command('run <pathArg>')
    .description('전체 파이프라인 (파일 또는 디렉토리)')
    .option('--no-move-done', '성공 시 입력 파일을 done/ 으로 이동하지 않음', false)
    .option('--output <path>', '출력 EPUB 경로')
    .action(async (pathArg, opts, cmd) => {
        applyLangOpts(cmd.optsWithGlobals());
        const moveDone = opts.moveDone !== false;
        const target = path.resolve(pathArg);
        if (fs.statSync(target).isDirectory()) {
            await runDirectory(target, { moveDone });
        } else {
            await runOne(target, { moveDone, output: opts.output });
        }
    });

program
    .command('extract <epub>')
    .description('EXTRACT 만 실행')
    .action(async (epub, _opts, cmd) => {
        applyLangOpts(cmd.optsWithGlobals());
        const work = workDirFor(epub);
        const ext = await extract(path.resolve(epub));
        if (!ext) return;
        fs.writeFileSync(path.join(work, 'segments.json'), JSON.stringify(ext, null, 2), 'utf8');
        log.ok(`segments.json 작성: ${path.join(work, 'segments.json')} (${ext.segments.length}건)`);
    });

program
    .command('translate <segmentsJson>')
    .description('segments.json 을 받아 translated.json 생성')
    .action(async (segPath, _opts, cmd) => {
        applyLangOpts(cmd.optsWithGlobals());
        const obj = JSON.parse(fs.readFileSync(segPath, 'utf8'));
        const segs = Array.isArray(obj) ? obj : obj.segments;
        const work = path.dirname(path.resolve(segPath));
        const translated = await translateSegments(segs, work);
        const out = path.join(work, 'translated.json');
        fs.writeFileSync(out, JSON.stringify(translated, null, 2), 'utf8');
        log.ok(`translated.json 작성: ${out}`);
    });

program
    .command('apply <epub> <translatedJson>')
    .description('원본 EPUB + translated.json 으로 출력 EPUB 생성')
    .option('--output <path>', '출력 EPUB 경로')
    .action(async (epub, jsonPath, opts, cmd) => {
        applyLangOpts(cmd.optsWithGlobals());
        const translated = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
        const out = opts.output || defaultOutPath(epub);
        await applyEpub(path.resolve(epub), translated, out);
    });

const tm = program.command('tm').description('TM 유틸리티');
tm.command('import <csv>')
    .description('CSV (src,tgt) 를 TM 으로 import')
    .action((csvPath) => {
        const db = tmConnect();
        const txt = fs.readFileSync(csvPath, 'utf8');
        const rows = txt.split(/\r?\n/).filter(Boolean);
        let n = 0;
        for (const r of rows) {
            const cells = parseCsvLine(r);
            if (cells.length < 2) continue;
            tmStore(db, cells[0], cells[1], '');
            n++;
        }
        db.close();
        log.ok(`TM import: ${n}건`);
    });

// 첫 인자가 .epub 파일/디렉토리면 'run' 으로 자동 라우팅
const argv = process.argv.slice();
const known = new Set(['run', 'extract', 'translate', 'apply', 'tm', '-h', '--help', '-V', '--version']);
if (argv.length >= 3) {
    // skip global options that take values
    let i = 2;
    while (i < argv.length && argv[i].startsWith('-')) {
        i += (argv[i] === '--in-lang' || argv[i] === '--out-lang') ? 2 : 1;
    }
    if (i < argv.length && !known.has(argv[i])) {
        argv.splice(i, 0, 'run');
    }
}
program.parseAsync(argv);
