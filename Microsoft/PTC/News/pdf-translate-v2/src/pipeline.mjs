import fs from 'node:fs';
import path from 'node:path';
import { log } from './util/log.mjs';
import { outputPath, workSubdir, safeStem } from './util/paths.mjs';
import { extractPages, applyEdits } from './pdf/engine.mjs';
import { addText, DEFAULT_FONT, DEFAULT_FONT_SIZE } from './pdf/edits.mjs';
import { tmGet, tmPut, tmDelete } from './tm/store.mjs';
import { loadGlossary } from './glossary/loader.mjs';
import { TokenMasker, restoreTokens, placeholdersEqual } from './glossary/masker.mjs';
import { translateBatch } from './translate/llm.mjs';

function emptyUsage() {
    return { inputTokens: 0, outputTokens: 0, totalTokens: 0 };
}

function addUsage(total, usage = {}) {
    total.inputTokens += usage.inputTokens || 0;
    total.outputTokens += usage.outputTokens || 0;
    total.totalTokens += usage.totalTokens || 0;
}

function listInputPdfs(inputDir) {
    if (!fs.existsSync(inputDir)) return [];
    return fs
        .readdirSync(inputDir)
        .filter((name) => !name.startsWith('~$') && path.extname(name).toLowerCase() === '.pdf')
        .map((name) => path.join(inputDir, name))
        .filter((filePath) => {
            try { return fs.statSync(filePath).isFile(); } catch { return false; }
        });
}

function moveToDone(filePath, doneDir) {
    fs.mkdirSync(doneDir, { recursive: true });
    let dest = path.join(doneDir, path.basename(filePath));
    if (fs.existsSync(dest)) {
        const ext = path.extname(dest);
        const stem = path.basename(dest, ext);
        const stamp = Date.now();
        dest = path.join(doneDir, `${stem}_${stamp}${ext}`);
    }
    fs.renameSync(filePath, dest);
    return dest;
}

function flattenSegments(pages) {
    // pages: [{ page, width, height, runs: [{ text, x, y, font_size, font_resource }] }]
    // 출력: [{ id, page, runIndex, x, y, fontSize, text }]
    const segments = [];
    for (const page of pages) {
        for (let i = 0; i < page.runs.length; i++) {
            const run = page.runs[i];
            const text = String(run.text || '');
            if (!text.trim()) continue;
            segments.push({
                id: segments.length,
                page: page.page,
                runIndex: i,
                x: run.x,
                y: run.y,
                fontSize: run.font_size || DEFAULT_FONT_SIZE,
                text,
            });
        }
    }
    return segments;
}

function writeJson(filePath, value) {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, JSON.stringify(value, null, 2), 'utf8');
}

function readJson(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

async function translateSegments(segments, cfg, glossary) {
    const masker = new TokenMasker(glossary.protectedTerms);
    const masked = segments.map((segment) => {
        const { masked: text, tokens } = masker.mask(segment.text);
        return { id: segment.id, text, tokens, original: segment.text };
    });

    const cache = new Map();
    const misses = [];
    for (const item of masked) {
        const cached = tmGet(cfg.tmDbPath, item.text, cfg.sourceLang, cfg.targetLang);
        if (cached != null && cached !== item.text) {
            cache.set(item.id, cached);
            continue;
        }
        if (cached === item.text) {
            tmDelete(cfg.tmDbPath, item.text, cfg.sourceLang, cfg.targetLang);
            log.warn(`원문 fallback TM 항목 삭제 (seg ${item.id}). 재번역 대상으로 처리합니다.`);
        }
        misses.push(item);
    }

    const usage = emptyUsage();
    let untranslated = 0;
    for (let i = 0; i < misses.length; i += cfg.batchSize) {
        const batch = misses.slice(i, i + cfg.batchSize);
        let outputs = [];
        try {
            const result = await translateBatch(batch, cfg, glossary.rows);
            outputs = result.texts;
            addUsage(usage, result.usage);
        } catch (err) {
            log.warn(`LLM 배치 실패 (${i}-${i + batch.length}): ${err.message}. segment 단위 재시도.`);
            for (const item of batch) {
                try {
                    const retry = await translateBatch([item], cfg, glossary.rows);
                    outputs.push(retry.texts[0]);
                    addUsage(usage, retry.usage);
                } catch (retryErr) {
                    log.warn(`LLM segment 재시도 실패 (seg ${item.id}): ${retryErr.message}. 원문 유지.`);
                    outputs.push(null);
                }
            }
        }
        for (let j = 0; j < batch.length; j++) {
            const item = batch[j];
            let output = outputs[j];
            let cacheable = true;
            if (output == null) {
                cache.set(item.id, null);
                untranslated += 1;
                continue;
            }
            if (!placeholdersEqual(item.text, output)) {
                log.warn(`placeholder 불일치 (seg ${item.id}). 원문 fallback.`);
                output = item.text;
                cacheable = false;
            }
            cache.set(item.id, output);
            if (cacheable && output !== item.text) {
                tmPut(cfg.tmDbPath, item.text, output, cfg.modelLabel, cfg.sourceLang, cfg.targetLang);
            }
        }
    }

    const translated = [];
    for (let i = 0; i < segments.length; i++) {
        const segment = segments[i];
        const maskedItem = masked[i];
        const cached = cache.get(maskedItem.id);
        if (cached == null) {
            translated.push({ ...segment, translated: null });
            continue;
        }
        translated.push({
            ...segment,
            translated: restoreTokens(cached, maskedItem.tokens),
        });
    }

    return {
        translated,
        stats: {
            total: segments.length,
            hits: segments.length - misses.length,
            misses: misses.length,
            untranslated,
            usage,
        },
    };
}

function buildEdits(translatedSegments, cfg) {
    const edits = [];
    for (const segment of translatedSegments) {
        const text = segment.translated;
        if (text == null) continue;
        if (text === segment.text && !cfg.keepOriginalLang) continue;
        edits.push(addText({
            page: segment.page,
            x: segment.x,
            y: segment.y,
            text,
            font: DEFAULT_FONT,
            size: segment.fontSize || DEFAULT_FONT_SIZE,
            color: [0, 0, 0],
        }));
    }
    return edits;
}

function writeError(workDir, sourceFilePath, reason, extra = {}) {
    const dir = workSubdir(workDir, sourceFilePath);
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(
        path.join(dir, 'error.json'),
        JSON.stringify({ source: sourceFilePath, reason: String(reason), ...extra, recordedAt: new Date().toISOString() }, null, 2),
        'utf8',
    );
}

export async function processFile(filePath, cfg) {
    const stem = safeStem(filePath);
    const workDir = workSubdir(cfg.workDir, filePath);
    fs.mkdirSync(workDir, { recursive: true });

    log.info(`PDF 처리 시작: ${filePath}`);

    let pages;
    try {
        pages = await extractPages(cfg, filePath);
    } catch (err) {
        writeError(cfg.workDir, filePath, `EXTRACT 실패: ${err.message}`);
        return { ok: false, skipped: false, reason: err.message };
    }

    const segments = flattenSegments(pages);
    writeJson(path.join(workDir, 'segments.json'), { stem, sourceLang: cfg.sourceLang, segments });
    log.info(`  EXTRACT: ${pages.length} 페이지, ${segments.length} 세그먼트`);

    if (segments.length === 0) {
        writeError(cfg.workDir, filePath, '추출된 텍스트 세그먼트가 없습니다.');
        return { ok: false, skipped: true, reason: 'empty' };
    }

    const glossary = loadGlossary(cfg.glossaryPath);

    let translatedResult;
    try {
        translatedResult = await translateSegments(segments, cfg, glossary);
    } catch (err) {
        writeError(cfg.workDir, filePath, `TRANSLATE 실패: ${err.message}`);
        return { ok: false, skipped: false, reason: err.message };
    }

    writeJson(path.join(workDir, 'translated.json'), {
        stem,
        sourceLang: cfg.sourceLang,
        targetLang: cfg.targetLang,
        segments: translatedResult.translated,
        stats: translatedResult.stats,
    });
    const stats = translatedResult.stats;
    log.info(`  TRANSLATE: hit ${stats.hits}, miss ${stats.misses}, untranslated ${stats.untranslated}, tokens in/out/total ${stats.usage.inputTokens}/${stats.usage.outputTokens}/${stats.usage.totalTokens}`);

    const edits = buildEdits(translatedResult.translated, cfg);
    const editsPath = path.join(workDir, 'edits.json');
    writeJson(editsPath, edits);

    if (edits.length === 0) {
        log.warn('적용할 EditOperation 이 없습니다 (모두 hit + 동일 또는 untranslated).');
    }

    const outPath = outputPath(cfg.outputDir, filePath, cfg.targetSuffix);
    try {
        await applyEdits(cfg, filePath, outPath, editsPath);
    } catch (err) {
        writeError(cfg.workDir, filePath, `APPLY 실패: ${err.message}`);
        return { ok: false, skipped: false, reason: err.message };
    }
    log.info(`  APPLY: ${outPath} (${edits.length} edits)`);

    if (!cfg.keepInput) {
        try {
            const dest = moveToDone(filePath, cfg.doneDir);
            log.info(`  DONE: 원본 -> ${dest}`);
        } catch (err) {
            log.warn(`원본 이동 실패: ${err.message}`);
        }
    }

    return { ok: true, outPath, segments: segments.length, stats };
}

export async function runPipeline(cfg) {
    for (const dir of [cfg.workDir, cfg.outputDir, cfg.inputDir, cfg.doneDir]) {
        fs.mkdirSync(dir, { recursive: true });
    }

    const files = listInputPdfs(cfg.inputDir);
    if (files.length === 0) {
        log.warn(`입력 PDF 없음: ${cfg.inputDir}`);
        return { total: 0, ok: 0, fail: 0, skipped: 0 };
    }

    let ok = 0;
    let fail = 0;
    let skipped = 0;
    for (const filePath of files) {
        try {
            const result = await processFile(filePath, cfg);
            if (result.ok) ok += 1;
            else if (result.skipped) skipped += 1;
            else fail += 1;
        } catch (err) {
            fail += 1;
            log.error(`실패: ${filePath}\n${err.stack || err.message}`);
            writeError(cfg.workDir, filePath, err.message || String(err));
        }
    }

    log.info(`결과: 성공 ${ok}/${files.length}, 스킵 ${skipped}, 실패 ${fail}`);
    return { total: files.length, ok, fail, skipped };
}

// 단계별 명령 (extract / translate / apply) 진입점

export async function extractOnly(pdfPath, cfg) {
    const stem = safeStem(pdfPath);
    const workDir = workSubdir(cfg.workDir, pdfPath);
    fs.mkdirSync(workDir, { recursive: true });
    const pages = await extractPages(cfg, pdfPath);
    const segments = flattenSegments(pages);
    const out = path.join(workDir, 'segments.json');
    writeJson(out, { stem, sourceLang: cfg.sourceLang, segments });
    log.info(`extract: ${pages.length} 페이지, ${segments.length} 세그먼트`);
    return out;
}

export async function translateOnly(segmentsJsonPath, cfg) {
    const data = readJson(segmentsJsonPath);
    if (!Array.isArray(data?.segments)) {
        throw new Error('segments.json 의 segments 배열을 찾을 수 없습니다.');
    }
    const glossary = loadGlossary(cfg.glossaryPath);
    const result = await translateSegments(data.segments, cfg, glossary);
    const out = path.join(path.dirname(segmentsJsonPath), 'translated.json');
    writeJson(out, {
        stem: data.stem,
        sourceLang: cfg.sourceLang,
        targetLang: cfg.targetLang,
        segments: result.translated,
        stats: result.stats,
    });
    return out;
}

export async function applyOnly(pdfPath, translatedJsonPath, cfg) {
    const data = readJson(translatedJsonPath);
    if (!Array.isArray(data?.segments)) {
        throw new Error('translated.json 의 segments 배열을 찾을 수 없습니다.');
    }
    const edits = buildEdits(data.segments, cfg);
    const editsPath = path.join(path.dirname(translatedJsonPath), 'edits.json');
    writeJson(editsPath, edits);
    const outPath = outputPath(cfg.outputDir, pdfPath, cfg.targetSuffix);
    await applyEdits(cfg, pdfPath, outPath, editsPath);
    return outPath;
}
