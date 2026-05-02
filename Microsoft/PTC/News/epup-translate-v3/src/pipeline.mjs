import fs from 'node:fs';
import path from 'node:path';
import { log } from './util/log.mjs';
import { loadGlossary } from './translate/glossary.mjs';
import { TokenMasker, restoreTokens, placeholdersEqual } from './translate/masker.mjs';
import { tmGet, tmPut } from './translate/tm.mjs';
import { translateBatch } from './translate/llm.mjs';
import {
    loadEpub,
    isDrmProtected,
    readContainer,
    readOpf,
    setOpfLanguage,
} from './epub/reader.mjs';
import {
    parseChapter,
    applyTranslations,
    setHtmlLang,
    serializeChapter,
} from './epub/xhtml.mjs';
import { writeEpub } from './epub/writer.mjs';

function moveToDone(filePath, doneDir) {
    fs.mkdirSync(doneDir, { recursive: true });
    const dest = path.join(doneDir, path.basename(filePath));
    fs.renameSync(filePath, dest);
}

async function translateChapter(zip, chapterPath, glossary, masker, cfg) {
    const entry = zip.file(chapterPath);
    if (!entry) {
        log.warn('chapter 누락:', chapterPath);
        return { translated: 0, hits: 0 };
    }
    const xml = await entry.async('string');
    const { document, segments } = parseChapter(xml);
    if (segments.length === 0) {
        setHtmlLang(document, cfg.targetLangTag);
        zip.file(chapterPath, serializeChapter(document));
        return { translated: 0, hits: 0 };
    }

    // Mask
    const masked = segments.map((s) => {
        const { masked: m, tokens } = masker.mask(s.text);
        return { id: s.id, text: m, tokens, original: s.text };
    });

    // TM lookup
    const misses = [];
    const cache = new Map();
    for (const m of masked) {
        const cached = tmGet(cfg.tmDbPath, m.text, cfg.sourceLang, cfg.targetLang);
        if (cached != null) {
            cache.set(m.id, cached);
        } else {
            misses.push(m);
        }
    }

    // Batch translate misses
    for (let i = 0; i < misses.length; i += cfg.batchSize) {
        const batch = misses.slice(i, i + cfg.batchSize);
        let outputs;
        try {
            outputs = await translateBatch(batch, cfg, glossary.rows);
        } catch (err) {
            log.warn(`LLM 배치 실패 (${chapterPath} ${i}-${i + batch.length}): ${err.message}. 원문 fallback.`);
            outputs = batch.map((b) => b.text);
        }
        for (let j = 0; j < batch.length; j++) {
            const item = batch[j];
            let out = outputs[j];
            let cacheable = true;
            if (!placeholdersEqual(item.text, out)) {
                log.warn(`placeholder 불일치 (${chapterPath} seg ${item.id}). 원문 fallback.`);
                out = item.text;
                cacheable = false;
            }
            cache.set(item.id, out);
            if (cacheable) {
                tmPut(cfg.tmDbPath, item.text, out, cfg.modelLabel, cfg.sourceLang, cfg.targetLang);
            }
        }
    }

    // Restore tokens & attach to segments
    let translatedCount = 0;
    for (let i = 0; i < segments.length; i++) {
        const seg = segments[i];
        const m = masked[i];
        const tgt = cache.get(m.id);
        if (tgt == null) continue;
        const restored = restoreTokens(tgt, m.tokens);
        seg.translated = restored;
        translatedCount += 1;
    }

    applyTranslations(document, segments);
    setHtmlLang(document, cfg.targetLangTag);
    zip.file(chapterPath, serializeChapter(document));
    return { translated: translatedCount, hits: cache.size - misses.length };
}

export async function translateEpubFile(filePath, cfg) {
    const stem = path.basename(filePath, path.extname(filePath));
    const outName = `${stem}_${cfg.targetSuffix}.epub`;
    const outPath = path.join(cfg.outputDir, outName);

    log.info('파일 처리 시작:', filePath);
    const zip = await loadEpub(filePath);

    if (isDrmProtected(zip)) {
        log.warn('DRM 보호 EPUB 감지 → 스킵:', filePath);
        return { ok: false, reason: 'DRM' };
    }

    const { opfPath } = await readContainer(zip);
    const opf = await readOpf(zip, opfPath);
    log.info(`OPF: ${opfPath}, XHTML 챕터: ${opf.xhtmlPaths.length}`);

    const glossary = loadGlossary(cfg.glossaryPath);
    const masker = new TokenMasker(glossary.protectedTerms);

    let totalSeg = 0;
    for (let i = 0; i < opf.xhtmlPaths.length; i++) {
        const cp = opf.xhtmlPaths[i];
        log.info(`  [${i + 1}/${opf.xhtmlPaths.length}] ${cp}`);
        const r = await translateChapter(zip, cp, glossary, masker, cfg);
        totalSeg += r.translated;
    }

    // Update OPF language
    const newOpf = setOpfLanguage(opf.rawXml, cfg.targetLangTag);
    zip.file(opfPath, newOpf);

    await writeEpub(zip, outPath);
    log.info(`출력: ${outPath} (총 번역 세그먼트 ${totalSeg})`);

    // move source to done/
    try {
        moveToDone(filePath, cfg.doneDir);
        log.info(`원본 이동 → ${cfg.doneDir}`);
    } catch (err) {
        log.warn(`원본 이동 실패: ${err.message}`);
    }
    return { ok: true, outPath, segments: totalSeg };
}

export async function runPipeline(cfg) {
    fs.mkdirSync(cfg.workDir, { recursive: true });
    fs.mkdirSync(cfg.outputDir, { recursive: true });
    fs.mkdirSync(cfg.inputDir, { recursive: true });

    const files = fs
        .readdirSync(cfg.inputDir)
        .filter((n) => n.toLowerCase().endsWith('.epub'))
        .map((n) => path.join(cfg.inputDir, n))
        .filter((p) => fs.statSync(p).isFile());

    if (files.length === 0) {
        log.warn(`입력 EPUB 없음: ${cfg.inputDir}/*.epub`);
        return { total: 0, ok: 0, fail: 0 };
    }

    let ok = 0;
    let fail = 0;
    for (const f of files) {
        try {
            const r = await translateEpubFile(f, cfg);
            if (r.ok) ok += 1;
            else fail += 1;
        } catch (err) {
            fail += 1;
            log.error(`실패: ${f}\n${err.stack || err.message}`);
        }
    }
    log.info(`결과: 성공 ${ok}/${files.length}, 실패 ${fail}`);
    return { total: files.length, ok, fail };
}
