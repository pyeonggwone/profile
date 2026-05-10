import fs from 'node:fs';
import path from 'node:path';
import { log } from './util/log.mjs';
import { outputPath, workSubdir, safeStem } from './util/paths.mjs';
import { extractPages, applyEdits } from './pdf/engine.mjs';
import { addFilledRect, addText, addTextEmbedded, addTextBoxEmbedded, DEFAULT_FONT, DEFAULT_FONT_SIZE } from './pdf/edits.mjs';
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

function pct(done, total) {
    if (!total) return '100.0%';
    return `${((done / total) * 100).toFixed(1)}%`;
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

function cleanExtractedText(value) {
    return String(value || '')
        .replace(/\u0000/g, '')
        .replace(/¶/g, '’')
        .replace(/[\u0001-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, '');
}

function estimateTextWidth(text, fontSize) {
    let units = 0;
    for (const ch of String(text || '')) {
        if (/\s/.test(ch)) units += 0.33;
        else if (/[,.;:!?')\]}>]/.test(ch)) units += 0.28;
        else if (/[([{<]/.test(ch)) units += 0.35;
        else if (/[^\x00-\x7F]/.test(ch)) units += 0.92;
        else if (/[ilI|]/.test(ch)) units += 0.28;
        else if (/[mwMW]/.test(ch)) units += 0.78;
        else units += 0.52;
    }
    return units * fontSize;
}

function rgbFromPdfInt(value, fallback = [0, 0, 0]) {
    if (Array.isArray(value) && value.length === 3) return value.map((item) => Math.max(0, Math.min(1, Number(item) || 0)));
    if (!Number.isFinite(Number(value))) return fallback;
    const number = Number(value) >>> 0;
    return [
        ((number >> 16) & 255) / 255,
        ((number >> 8) & 255) / 255,
        (number & 255) / 255,
    ].map((item) => Number(item.toFixed(4)));
}

function dominantBoolean(runs, key) {
    return runs.filter((run) => !!run[key]).length >= Math.ceil(runs.length / 2);
}

function firstArray(runs, key, fallback) {
    const found = runs.find((run) => Array.isArray(run[key]) && run[key].length === 3);
    return found ? found[key].map((item) => Math.max(0, Math.min(1, Number(item) || 0))) : fallback;
}

function joinRuns(runs) {
    let out = '';
    let currentEnd = 0;
    for (const run of runs) {
        const text = cleanExtractedText(run.text);
        if (!text.trim()) continue;
        const fontSize = run.font_size || DEFAULT_FONT_SIZE;
        const runEnd = run.x + estimateTextWidth(text, fontSize);
        if (!out) {
            out = text;
            currentEnd = runEnd;
            continue;
        }
        const gap = run.x - currentEnd;
        const noSpaceBefore = /^[,.;:!?')\]}>’]/.test(text);
        const noSpaceAfter = /[([{<’]$/.test(out) || /\s$/.test(out);
        const sameWord = gap < Math.max(1.8, fontSize * 0.45);
        out += noSpaceBefore || noSpaceAfter || sameWord ? text : ` ${text}`;
        currentEnd = Math.max(currentEnd, runEnd);
    }
    return out.replace(/\s+/g, ' ').trim();
}

function splitVisualLine(runs, pageWidth) {
    const sorted = [...runs].sort((a, b) => a.x - b.x);
    const groups = [];
    let current = [];
    let currentEnd = 0;
    for (const run of sorted) {
        const fontSize = run.font_size || DEFAULT_FONT_SIZE;
        const text = cleanExtractedText(run.text);
        if (!text.trim()) continue;
        const estimatedWidth = estimateTextWidth(text, fontSize);
        const gap = current.length ? run.x - currentEnd : 0;
        if (current.length && gap > Math.max(42, fontSize * 4.2)) {
            groups.push(current);
            current = [];
        }
        current.push({ ...run, text });
        currentEnd = Math.max(currentEnd, run.x + estimatedWidth);
    }
    if (current.length) groups.push(current);
    return groups.map((group) => {
        const x = Math.min(...group.map((run) => run.x));
        const left = Math.min(...group.map((run) => Number.isFinite(run.left) ? run.left : run.x));
        const y = group.reduce((sum, run) => sum + run.y, 0) / group.length;
        const top = Math.min(...group.map((run) => Number.isFinite(run.top) ? run.top : run.y - (run.font_size || DEFAULT_FONT_SIZE)));
        const bottom = Math.max(...group.map((run) => Number.isFinite(run.bottom) ? run.bottom : run.y + 2));
        const right = Math.max(...group.map((run) => Number.isFinite(run.right) ? run.right : run.x + estimateTextWidth(run.text, run.font_size || DEFAULT_FONT_SIZE)));
        const fontSize = Math.max(...group.map((run) => run.font_size || DEFAULT_FONT_SIZE));
        const estimatedEnd = Math.max(...group.map((run) => run.x + estimateTextWidth(run.text, run.font_size || fontSize)));
        const text = joinRuns(group);
        const naturalWidth = Math.max(estimateTextWidth(text, fontSize), estimatedEnd - x);
        const bboxWidth = Math.max(0, right - left);
        return {
            x,
            y,
            left,
            right,
            top,
            bottom,
            height: Math.max(bottom - top, fontSize * 1.35),
            fontSize,
            font: group[0]?.font || group[0]?.font_resource || '',
            bold: dominantBoolean(group, 'bold'),
            italic: dominantBoolean(group, 'italic'),
            serif: dominantBoolean(group, 'serif'),
            monospace: dominantBoolean(group, 'monospace'),
            color: firstArray(group, 'color_rgb', rgbFromPdfInt(group[0]?.color)),
            bgColor: firstArray(group, 'bg_color', [1, 1, 1]),
            text,
            maxWidth: Math.max(24, Math.min(pageWidth - x - 12, bboxWidth || naturalWidth + 2)),
            sourceRunCount: group.length,
        };
    }).filter((line) => line.text.trim());
}

function flattenSegments(pages) {
    const segments = [];
    for (const page of pages) {
        const pageWidth = page.width || 612;
        const runs = (page.runs || [])
            .map((run, index) => ({ ...run, index, text: cleanExtractedText(run.text) }))
            .filter((run) => run.text.trim())
            .sort((a, b) => (a.y - b.y) || (a.x - b.x));
        const visualLines = [];
        for (const run of runs) {
            const tolerance = Math.max(2.2, (run.font_size || DEFAULT_FONT_SIZE) * 0.45);
            let line = visualLines.find((candidate) => Math.abs(candidate.y - run.y) <= tolerance);
            if (!line) {
                line = { y: run.y, runs: [] };
                visualLines.push(line);
            }
            line.runs.push(run);
            line.y = line.runs.reduce((sum, item) => sum + item.y, 0) / line.runs.length;
        }
        visualLines.sort((a, b) => (a.y - b.y) || (Math.min(...a.runs.map((run) => run.x)) - Math.min(...b.runs.map((run) => run.x))));
        for (const visualLine of visualLines) {
            for (const line of splitVisualLine(visualLine.runs, pageWidth)) {
                segments.push({
                    id: segments.length,
                    page: page.page,
                    runIndex: visualLine.runs[0]?.index || 0,
                    x: line.x,
                    y: line.y,
                    left: line.left,
                    right: line.right,
                    top: line.top,
                    bottom: line.bottom,
                    height: line.height,
                    fontSize: line.fontSize,
                    font: line.font,
                    bold: line.bold,
                    italic: line.italic,
                    serif: line.serif,
                    monospace: line.monospace,
                    color: line.color,
                    bgColor: line.bgColor,
                    maxWidth: line.maxWidth,
                    sourceRunCount: line.sourceRunCount,
                    text: line.text,
                });
            }
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
    let retryBatches = 0;
    let retryRecovered = 0;
    let retryFailed = 0;
    let lastProgressLogged = 0;
    if (misses.length === 0) {
        log.info(`  TRANSLATE: TM hit ${segments.length}/${segments.length}, LLM 호출 없음`);
    } else {
        log.info(`  TRANSLATE 시작: total ${segments.length}, TM hit ${segments.length - misses.length}, LLM 대상 ${misses.length}, batchSize ${cfg.batchSize}`);
    }
    for (let i = 0; i < misses.length; i += cfg.batchSize) {
        const batch = misses.slice(i, i + cfg.batchSize);
        let outputs = [];
        const batchLabel = `${i}-${i + batch.length}`;
        try {
            const result = await translateBatch(batch, cfg, glossary.rows);
            outputs = result.texts;
            addUsage(usage, result.usage);
            log.info(`  TRANSLATE batch 성공 (${batchLabel}) ${pct(i + batch.length, misses.length)} tokens ${result.usage.inputTokens}/${result.usage.outputTokens}/${result.usage.totalTokens}`);
        } catch (err) {
            retryBatches += 1;
            log.warn(`  TRANSLATE batch 실패 (${batchLabel}) ${pct(i + batch.length, misses.length)}: ${err.message}. segment 단위 재시도 시작.`);
            let batchRecovered = 0;
            let batchFailed = 0;
            for (const item of batch) {
                try {
                    const retry = await translateBatch([item], cfg, glossary.rows);
                    outputs.push(retry.texts[0]);
                    addUsage(usage, retry.usage);
                    batchRecovered += 1;
                    retryRecovered += 1;
                    log.info(`    retry 성공 seg ${item.id}: "${item.original.slice(0, 80)}" -> "${retry.texts[0].slice(0, 80)}"`);
                } catch (retryErr) {
                    batchFailed += 1;
                    retryFailed += 1;
                    log.error(`    retry 실패 seg ${item.id}: ${retryErr.message}. 원문 유지. source="${item.original.slice(0, 160)}"`);
                    outputs.push(null);
                }
            }
            log.warn(`  TRANSLATE batch 재시도 결과 (${batchLabel}): 복구 ${batchRecovered}/${batch.length}, 실패 ${batchFailed}/${batch.length}`);
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
                log.warn(`placeholder 불일치 (seg ${item.id}). 원문 fallback. source="${item.original.slice(0, 120)}" output="${String(output).slice(0, 120)}"`);
                output = item.text;
                cacheable = false;
            }
            cache.set(item.id, output);
            if (cacheable && output !== item.text) {
                tmPut(cfg.tmDbPath, item.text, output, cfg.modelLabel, cfg.sourceLang, cfg.targetLang);
            }
        }
        const completed = i + batch.length;
        if (completed - lastProgressLogged >= cfg.batchSize * 10 || completed === misses.length) {
            lastProgressLogged = completed;
            log.info(`  TRANSLATE 진행: LLM ${completed}/${misses.length} (${pct(completed, misses.length)}), retry batch ${retryBatches}, retry 복구 ${retryRecovered}, retry 실패 ${retryFailed}, untranslated ${untranslated}`);
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
            retryBatches,
            retryRecovered,
            retryFailed,
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
        const baseSize = segment.fontSize || DEFAULT_FONT_SIZE;
        const maxWidth = Math.max(24, Number(segment.maxWidth) || estimateTextWidth(segment.text, baseSize) || 160);
        const fontScale = ['kr', 'ch', 'jp'].includes(cfg.targetLang) ? cfg.pdfCjkSizeRatio : 1;
        const styleScale = segment.bold ? 0.98 : 1;
        const targetBaseSize = baseSize * fontScale * styleScale;
        const translatedWidth = estimateTextWidth(text, targetBaseSize);
        const fitSize = translatedWidth > maxWidth
            ? Math.max(cfg.pdfMinFontSize, Math.min(targetBaseSize, targetBaseSize * (maxWidth / translatedWidth)))
            : targetBaseSize;
        const top = Number.isFinite(segment.top) ? segment.top : segment.y - baseSize * 0.95;
        const left = Number.isFinite(segment.left) ? segment.left : segment.x;
        const right = Number.isFinite(segment.right) ? segment.right : segment.x + maxWidth;
        const erasePadding = Math.max(0, Number(cfg.pdfErasePadding) || 0);
        const rectHeight = Math.max(Number(segment.height) || 0, baseSize * 1.12, fitSize * 1.42);
        const rectY = Math.max(0, top + erasePadding);
        const rectX = Math.max(0, left + erasePadding);
        const rectWidth = Math.max(0, (right - left) - erasePadding * 2);
        edits.push(addFilledRect({
            page: segment.page,
            x: rectX,
            y: rectY,
            width: rectWidth || maxWidth,
            height: Math.max(0, rectHeight - erasePadding * 2),
            color: segment.bgColor || [1, 1, 1],
        }));
        if ((cfg.pdfEngine || 'pymupdf') === 'pymupdf' && cfg.pdfFontPath) {
            const fontPath = segment.bold && cfg.pdfBoldFontPath ? cfg.pdfBoldFontPath : cfg.pdfFontPath;
            edits.push(addTextBoxEmbedded({
                page: segment.page,
                x: left,
                y: Math.max(0, top),
                width: Math.max(8, right - left),
                height: Math.max(8, rectHeight + 1),
                text,
                fontPath,
                fontName: segment.bold && cfg.pdfBoldFontPath ? 'PDFTrBold' : 'PDFTrRegular',
                size: fitSize,
                color: segment.color || [0, 0, 0],
            }));
            continue;
        }
        const add = cfg.pdfFontPath ? addTextEmbedded : addText;
        edits.push(add({
            page: segment.page,
            x: segment.x,
            y: segment.y,
            text,
            fontPath: cfg.pdfFontPath,
            font: DEFAULT_FONT,
            size: fitSize,
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

function clearError(workDir, sourceFilePath) {
    const filePath = path.join(workSubdir(workDir, sourceFilePath), 'error.json');
    if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
}

export async function processFile(filePath, cfg) {
    const stem = safeStem(filePath);
    const workDir = workSubdir(cfg.workDir, filePath);
    fs.mkdirSync(workDir, { recursive: true });
    clearError(cfg.workDir, filePath);

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
    log.info(`  TRANSLATE: hit ${stats.hits}, miss ${stats.misses}, untranslated ${stats.untranslated}, retry batch ${stats.retryBatches}, retry 복구 ${stats.retryRecovered}, retry 실패 ${stats.retryFailed}, tokens in/out/total ${stats.usage.inputTokens}/${stats.usage.outputTokens}/${stats.usage.totalTokens}`);

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
            else if (result.skipped) {
                skipped += 1;
                log.warn(`스킵: ${filePath} (${result.reason || 'unknown'})`);
            } else {
                fail += 1;
                log.error(`실패: ${filePath} (${result.reason || 'unknown'})`);
            }
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
    clearError(cfg.workDir, pdfPath);
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
