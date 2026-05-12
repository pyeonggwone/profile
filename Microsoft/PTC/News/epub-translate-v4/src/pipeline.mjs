import fs from 'node:fs';
import path from 'node:path';
import { detectInput } from './formats/detect.mjs';
import { adapterFor } from './formats/index.mjs';
import { translateSegments } from './translate/engine.mjs';
import { loadGlossary } from './translate/glossary.mjs';
import { writeBookMetadata } from './metadata/writer.mjs';
import { createBaseMetadata, finishMetadata, markFailed, markSkipped } from './metadata/collector.mjs';
import { log } from './util/log.mjs';

const SUPPORTED_EXTENSIONS = new Set(['.epub', '.azw3', '.mobi', '.kfx']);

function ensureDirs(cfg) {
    for (const dir of [cfg.inputDir, cfg.outputDir, cfg.workDir, cfg.doneDir, cfg.metadataDir]) {
        fs.mkdirSync(dir, { recursive: true });
    }
}

function listInputFiles(inputPath) {
    const stat = fs.existsSync(inputPath) ? fs.statSync(inputPath) : null;
    if (!stat) return [];
    if (stat.isFile()) return [inputPath];
    return fs
        .readdirSync(inputPath)
        .map((name) => path.join(inputPath, name))
        .filter((filePath) => fs.statSync(filePath).isFile())
        .filter((filePath) => SUPPORTED_EXTENSIONS.has(path.extname(filePath).toLowerCase()));
}

function outputPathFor(filePath, format, cfg) {
    const stem = path.basename(filePath, path.extname(filePath));
    return path.join(cfg.outputDir, `${stem}_${cfg.targetSuffix}.${format}`);
}

function moveToDone(filePath, doneDir) {
    fs.mkdirSync(doneDir, { recursive: true });
    const dest = path.join(doneDir, path.basename(filePath));
    if (fs.existsSync(dest)) fs.rmSync(dest, { force: true });
    fs.renameSync(filePath, dest);
}

export async function processFile(filePath, cfg, glossary) {
    const startedAt = new Date();
    let metadata = createBaseMetadata(filePath, cfg, startedAt);
    log.info('파일 처리 시작:', filePath);

    try {
        const detected = await detectInput(filePath);
        metadata.format = detected.format || '';
        metadata.warnings.push(...detected.warnings);

        if (cfg.onlyFormat && detected.format !== cfg.onlyFormat) {
            metadata = markSkipped(metadata, `format filtered: ${cfg.onlyFormat}`);
            await writeBookMetadata(metadata, cfg);
            return { ok: false, skipped: true };
        }

        if (!detected.supported) {
            metadata = markSkipped(metadata, detected.reason || 'unsupported format');
            await writeBookMetadata(metadata, cfg);
            return { ok: false, skipped: true };
        }

        const adapter = adapterFor(detected.format);
        const book = await adapter.read(filePath, cfg, detected);
        metadata = { ...metadata, ...book.metadata, format: detected.format };
        metadata.warnings.push(...(book.warnings || []));

        if (book.skipped) {
            metadata = markSkipped(metadata, book.reason || 'skipped by adapter');
            await writeBookMetadata(metadata, cfg);
            return { ok: false, skipped: true };
        }

        const translation = await translateSegments(book.segments, cfg, glossary);
        const outPath = outputPathFor(filePath, detected.format, cfg);
        await adapter.write(book, translation.translations, cfg, outPath);

        metadata.outputFile = path.basename(outPath);
        metadata.totalWordCount = translation.totalWordCount;
        metadata.translatedSegmentCount = translation.translatedSegmentCount;
        metadata.skippedSegmentCount = translation.skippedSegmentCount;
        metadata.tmHitCount = translation.tmHitCount;
        metadata.tmMissCount = translation.tmMissCount;
        metadata.inputTokenCount = translation.usage.inputTokens;
        metadata.outputTokenCount = translation.usage.outputTokens;
        metadata.totalTokenCount = translation.usage.totalTokens;
        metadata.model = cfg.modelLabel;
        metadata = finishMetadata(metadata, startedAt, 'success');
        await writeBookMetadata(metadata, cfg);

        moveToDone(filePath, cfg.doneDir);
        log.info(`출력: ${outPath}`);
        return { ok: true, outPath };
    } catch (err) {
        metadata = markFailed(metadata, err.message || String(err), startedAt);
        await writeBookMetadata(metadata, cfg);
        log.error(`실패: ${filePath}\n${err.stack || err.message}`);
        return { ok: false, error: err };
    }
}

export async function runPipeline(cfg) {
    ensureDirs(cfg);
    const files = listInputFiles(cfg.inputPath);
    if (files.length === 0) {
        log.warn(`입력 파일 없음: ${cfg.inputPath}`);
        return { total: 0, ok: 0, fail: 0, skipped: 0 };
    }

    const glossary = loadGlossary(cfg.glossaryPath);
    let ok = 0;
    let fail = 0;
    let skipped = 0;

    for (const filePath of files) {
        const result = await processFile(filePath, cfg, glossary);
        if (result.ok) ok += 1;
        else if (result.skipped) skipped += 1;
        else fail += 1;
    }

    log.info(`결과: 성공 ${ok}/${files.length}, 스킵 ${skipped}, 실패 ${fail}`);
    return { total: files.length, ok, fail, skipped };
}
