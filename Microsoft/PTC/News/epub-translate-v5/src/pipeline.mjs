import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { log } from './util/log.mjs';
import { loadGlossary } from './translate/glossary.mjs';
import { TokenMasker, restoreTokens, placeholdersEqual } from './translate/masker.mjs';
import { tmDelete, tmGet, tmPut } from './translate/tm.mjs';
import { translateBatch } from './translate/llm.mjs';
import { detectInput } from './formats/detect.mjs';
import { writeFormatStatus } from './formats/status.mjs';
import { loadEpub, isDrmProtected, readContainer, readOpf, setOpfLanguage } from './epub/reader.mjs';
import { parseChapter, applyTranslations, setHtmlLang, serializeChapter } from './epub/xhtml.mjs';
import { writeEpub } from './epub/writer.mjs';

const SUPPORTED_EXTENSIONS = new Set(['.epub', '.azw3', '.mobi', '.kfx']);

function emptyUsage() {
    return { inputTokens: 0, outputTokens: 0, totalTokens: 0 };
}

function addUsage(total, usage = {}) {
    total.inputTokens += usage.inputTokens || 0;
    total.outputTokens += usage.outputTokens || 0;
    total.totalTokens += usage.totalTokens || 0;
}

function countWords(text) {
    const normalized = String(text || '').trim();
    if (!normalized) return 0;
    const matches = normalized.match(/[\p{L}\p{N}]+(?:['’-][\p{L}\p{N}]+)*/gu);
    return matches ? matches.length : 0;
}

function safeStem(filePath) {
    return path.basename(filePath, path.extname(filePath)).replace(/[<>:"/\\|?*]+/g, '_');
}

function resolvePathCommand(command) {
    const pathExt = process.platform === 'win32' ? (process.env.PATHEXT || '.EXE;.CMD;.BAT;.COM').split(';') : [''];
    const pathDirs = (process.env.PATH || '').split(path.delimiter).filter(Boolean);
    const names = process.platform === 'win32' && !path.extname(command)
        ? pathExt.map((extension) => `${command}${extension.toLowerCase()}`)
        : [command, `${command}.exe`];

    for (const dir of pathDirs) {
        for (const name of names) {
            if (fs.existsSync(path.join(dir, name))) return name;
        }
    }
    return '';
}

function windowsPathToWslPath(value) {
    if (process.platform === 'win32') return value;
    const match = String(value || '').match(/^([A-Za-z]):[\\/](.*)$/);
    if (!match) return value;
    return `/mnt/${match[1].toLowerCase()}/${match[2].replace(/\\/g, '/')}`;
}

function firstExistingPath(candidates) {
    for (const candidate of candidates) {
        if (candidate && fs.existsSync(candidate)) return candidate;
    }
    return '';
}

function resolveEbookConvert() {
    const configured = process.env.EBOOK_CONVERT_PATH || process.env.CALIBRE_EBOOK_CONVERT;
    if (configured) {
        const resolved = firstExistingPath([configured, windowsPathToWslPath(configured)]);
        if (!resolved) throw new Error(`ebook-convert 실행 파일을 찾지 못했습니다: ${configured}`);
        return resolved;
    }

    const windowsCandidates = [
        'C:\\Program Files\\Calibre2\\ebook-convert.exe',
        'C:\\Program Files (x86)\\Calibre2\\ebook-convert.exe',
    ];
    const windowsResolved = firstExistingPath(windowsCandidates.flatMap((candidate) => [candidate, windowsPathToWslPath(candidate)]));
    if (windowsResolved) return windowsResolved;

    const pathCommand = resolvePathCommand('ebook-convert');
    if (pathCommand) return pathCommand;
    throw new Error('AZW3 번역에는 Calibre CLI ebook-convert가 필요합니다. Calibre 설치 후 PATH에 추가하거나 EBOOK_CONVERT_PATH를 설정하세요.');
}

function runCommand(command, args) {
    return new Promise((resolve, reject) => {
        const child = spawn(command, args, { stdio: ['ignore', 'pipe', 'pipe'] });
        let stdout = '';
        let stderr = '';
        child.stdout.on('data', (chunk) => { stdout += chunk.toString(); });
        child.stderr.on('data', (chunk) => { stderr += chunk.toString(); });
        child.on('error', reject);
        child.on('close', (code) => {
            if (code === 0) resolve({ stdout, stderr });
            else reject(new Error(`${command} 종료 코드 ${code}: ${(stderr || stdout).trim()}`));
        });
    });
}

function moveToDone(filePath, doneDir) {
    fs.mkdirSync(doneDir, { recursive: true });
    const dest = path.join(doneDir, path.basename(filePath));
    if (fs.existsSync(dest)) fs.rmSync(dest, { force: true });
    fs.renameSync(filePath, dest);
}

async function translateChapter(zip, chapterPath, glossary, masker, cfg) {
    const entry = zip.file(chapterPath);
    if (!entry) {
        log.warn('chapter 누락:', chapterPath);
        return { translated: 0, untranslated: 0, hits: 0, misses: 0, sourceWords: 0, usage: emptyUsage() };
    }
    const xml = await entry.async('string');
    const { document, segments } = parseChapter(xml);
    if (segments.length === 0) {
        setHtmlLang(document, cfg.targetLangTag);
        zip.file(chapterPath, serializeChapter(document));
        return { translated: 0, untranslated: 0, hits: 0, misses: 0, sourceWords: 0, usage: emptyUsage() };
    }

    const sourceWords = segments.reduce((sum, segment) => sum + countWords(segment.text), 0);

    const masked = segments.map((segment) => {
        const { masked: text, tokens } = masker.mask(segment.text);
        return { id: segment.id, text, tokens, original: segment.text };
    });

    const misses = [];
    const cache = new Map();
    for (const item of masked) {
        const cached = tmGet(cfg.tmDbPath, item.text, cfg.sourceLang, cfg.targetLang);
        if (cached != null && cached !== item.text) {
            cache.set(item.id, cached);
        } else {
            if (cached === item.text) {
                tmDelete(cfg.tmDbPath, item.text, cfg.sourceLang, cfg.targetLang);
                log.warn(`원문 fallback TM 항목 삭제 (${chapterPath} seg ${item.id}). 재번역 대상으로 처리합니다.`);
            }
            misses.push(item);
        }
    }

    const usage = emptyUsage();
    for (let i = 0; i < misses.length; i += cfg.batchSize) {
        const batch = misses.slice(i, i + cfg.batchSize);
        let outputs = [];
        try {
            const result = await translateBatch(batch, cfg, glossary.rows);
            outputs = result.texts;
            addUsage(usage, result.usage);
        } catch (err) {
            log.warn(`LLM 배치 실패 (${chapterPath} ${i}-${i + batch.length}): ${err.message}. segment 단위 재시도.`);
            for (const item of batch) {
                try {
                    const retry = await translateBatch([item], cfg, glossary.rows);
                    outputs.push(retry.texts[0]);
                    addUsage(usage, retry.usage);
                } catch (retryErr) {
                    log.warn(`LLM segment 재시도 실패 (${chapterPath} seg ${item.id}): ${retryErr.message}. 원문 유지.`);
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
                continue;
            }
            if (!placeholdersEqual(item.text, output)) {
                log.warn(`placeholder 불일치 (${chapterPath} seg ${item.id}). 원문 fallback.`);
                output = item.text;
                cacheable = false;
            }
            cache.set(item.id, output);
            if (cacheable && output !== item.text) {
                tmPut(cfg.tmDbPath, item.text, output, cfg.modelLabel, cfg.sourceLang, cfg.targetLang);
            }
        }
    }

    let translatedCount = 0;
    let untranslatedCount = 0;
    for (let i = 0; i < segments.length; i++) {
        const segment = segments[i];
        const maskedItem = masked[i];
        const translated = cache.get(maskedItem.id);
        if (translated == null) {
            untranslatedCount += 1;
            continue;
        }
        segment.translated = restoreTokens(translated, maskedItem.tokens);
        translatedCount += 1;
    }

    applyTranslations(document, segments);
    setHtmlLang(document, cfg.targetLangTag);
    zip.file(chapterPath, serializeChapter(document));
    return { translated: translatedCount, untranslated: untranslatedCount, hits: cache.size - misses.length, misses: misses.length, sourceWords, usage };
}

async function translateEpubFile(filePath, cfg, options = {}) {
    const sourceFilePath = options.sourceFilePath || filePath;
    const sourceFormat = options.sourceFormat || 'epub';
    const stem = options.outputStem || path.basename(sourceFilePath, path.extname(sourceFilePath));
    const outName = `${stem}_${cfg.targetSuffix}.epub`;
    const outPath = path.join(cfg.outputDir, outName);

    log.info('EPUB 처리 시작:', filePath);
    const zip = await loadEpub(filePath);

    if (isDrmProtected(zip)) {
        log.warn('DRM 보호 EPUB 감지 -> 스킵:', filePath);
        await writeFormatStatus(sourceFilePath, sourceFormat, 'skipped', 'DRM protected', cfg);
        return { ok: false, skipped: true, reason: 'DRM' };
    }

    const { opfPath } = await readContainer(zip);
    const opf = await readOpf(zip, opfPath);
    log.info(`OPF: ${opfPath}, XHTML 챕터: ${opf.xhtmlPaths.length}`);

    const glossary = loadGlossary(cfg.glossaryPath);
    const masker = new TokenMasker(glossary.protectedTerms);

    let totalSegments = 0;
    let totalSourceWords = 0;
    let tmHitCount = 0;
    let tmMissCount = 0;
    let untranslatedSegmentCount = 0;
    const totalUsage = emptyUsage();
    for (let i = 0; i < opf.xhtmlPaths.length; i++) {
        const chapterPath = opf.xhtmlPaths[i];
        log.info(`  [${i + 1}/${opf.xhtmlPaths.length}] ${chapterPath}`);
        const result = await translateChapter(zip, chapterPath, glossary, masker, cfg);
        totalSegments += result.translated;
        untranslatedSegmentCount += result.untranslated;
        totalSourceWords += result.sourceWords;
        tmHitCount += result.hits;
        tmMissCount += result.misses;
        addUsage(totalUsage, result.usage);
    }

    zip.file(opfPath, setOpfLanguage(opf.rawXml, cfg.targetLangTag));
    await writeEpub(zip, outPath);
    log.info(`출력: ${outPath} (총 번역 세그먼트 ${totalSegments})`);

    const status = untranslatedSegmentCount > 0 ? 'partial' : 'success';
    const reason = untranslatedSegmentCount > 0 ? `${untranslatedSegmentCount} segment(s) were not translated after retry.` : '';
    await writeFormatStatus(sourceFilePath, sourceFormat, status, reason, cfg, {
        outputFile: path.basename(outPath),
        translatedSegmentCount: totalSegments,
        untranslatedSegmentCount,
        sourceWordCount: totalSourceWords,
        inputTokenCount: totalUsage.inputTokens,
        outputTokenCount: totalUsage.outputTokens,
        totalTokenCount: totalUsage.totalTokens,
        tmHitCount,
        tmMissCount,
    });

    if (options.moveSource !== false) {
        try {
            moveToDone(sourceFilePath, cfg.doneDir);
            log.info(`원본 이동 -> ${cfg.doneDir}`);
        } catch (err) {
            log.warn(`원본 이동 실패: ${err.message}`);
        }
    }

    return { ok: true, outPath, segments: totalSegments };
}

async function convertAzw3ToEpub(filePath, cfg) {
    const ebookConvert = resolveEbookConvert();
    const convertedDir = path.join(cfg.workDir, 'converted');
    fs.mkdirSync(convertedDir, { recursive: true });
    const convertedPath = path.join(convertedDir, `${safeStem(filePath)}.epub`);
    if (fs.existsSync(convertedPath)) fs.rmSync(convertedPath, { force: true });

    log.info('AZW3 -> EPUB 변환 시작:', filePath);
    await runCommand(ebookConvert, [filePath, convertedPath]);
    if (!fs.existsSync(convertedPath)) throw new Error(`AZW3 변환 결과 EPUB이 생성되지 않았습니다: ${convertedPath}`);
    log.info('AZW3 변환 완료:', convertedPath);
    return convertedPath;
}

async function translateAzw3File(filePath, detected, cfg) {
    try {
        const convertedPath = await convertAzw3ToEpub(filePath, cfg);
        const result = await translateEpubFile(convertedPath, cfg, {
            sourceFilePath: filePath,
            sourceFormat: 'azw3',
            outputStem: path.basename(filePath, path.extname(filePath)),
            moveSource: false,
        });
        if (result.ok) {
            try {
                moveToDone(filePath, cfg.doneDir);
                log.info(`원본 이동 -> ${cfg.doneDir}`);
            } catch (err) {
                log.warn(`원본 이동 실패: ${err.message}`);
            }
        }
        return result;
    } catch (err) {
        const reason = err.message || String(err);
        await writeFormatStatus(filePath, 'azw3', 'failed', err.message || String(err), cfg, {
            confidence: detected.confidence,
            warnings: detected.warnings,
        });
        log.error(`AZW3 처리 실패: ${filePath}\n${reason}`);
        return { ok: false, skipped: false, reason };
    }
}

async function processUnsupportedMvp1(filePath, detected, cfg) {
    const reason = `${detected.format.toUpperCase()} MVP1: detection/status only. Text extraction and writer are tracked in TODO.md.`;
    log.warn(reason, filePath);
    await writeFormatStatus(filePath, detected.format, 'skipped', reason, cfg, {
        confidence: detected.confidence,
        warnings: detected.warnings,
    });
    return { ok: false, skipped: true, reason };
}

export async function processFile(filePath, cfg) {
    const detected = await detectInput(filePath);
    if (cfg.onlyFormat && detected.format !== cfg.onlyFormat) {
        return { ok: false, skipped: true, reason: `format filtered: ${cfg.onlyFormat}` };
    }
    if (!detected.supported) {
        await writeFormatStatus(filePath, detected.format || 'unknown', 'skipped', detected.reason, cfg, detected);
        return { ok: false, skipped: true, reason: detected.reason };
    }
    if (detected.format === 'azw3') return translateAzw3File(filePath, detected, cfg);
    if (detected.format !== 'epub') return processUnsupportedMvp1(filePath, detected, cfg);
    return translateEpubFile(filePath, cfg);
}

export async function runPipeline(cfg) {
    for (const dir of [cfg.workDir, cfg.outputDir, cfg.inputDir, cfg.doneDir, cfg.metadataDir]) {
        fs.mkdirSync(dir, { recursive: true });
    }

    const files = fs
        .readdirSync(cfg.inputDir)
        .filter((name) => SUPPORTED_EXTENSIONS.has(path.extname(name).toLowerCase()))
        .map((name) => path.join(cfg.inputDir, name))
        .filter((filePath) => fs.statSync(filePath).isFile());

    if (files.length === 0) {
        log.warn(`입력 파일 없음: ${cfg.inputDir}`);
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
            await writeFormatStatus(filePath, 'unknown', 'failed', err.message || String(err), cfg);
        }
    }

    log.info(`결과: 성공 ${ok}/${files.length}, 스킵 ${skipped}, 실패 ${fail}`);
    return { total: files.length, ok, fail, skipped };
}