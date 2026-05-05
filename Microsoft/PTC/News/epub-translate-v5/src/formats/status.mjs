import fs from 'node:fs';
import path from 'node:path';

function safeStem(filePath) {
    return path.basename(filePath, path.extname(filePath)).replace(/[<>:"/\\|?*]+/g, '_');
}

function mvpStage(format) {
    if (format === 'epub') return 'MVP 1 EPUB';
    if (format === 'azw3') return 'MVP 2 AZW3 Calibre conversion';
    return 'MVP 1 detection/status';
}

export async function writeFormatStatus(filePath, format, status, reason, cfg, extra = {}) {
    fs.mkdirSync(cfg.metadataDir, { recursive: true });
    const now = new Date().toISOString();
    const metadata = {
        schemaVersion: '1.0',
        sourceFile: path.basename(filePath),
        outputFile: extra.outputFile || '',
        format,
        status,
        reason,
        mvpStage: extra.mvpStage || mvpStage(format),
        translatedSegmentCount: extra.translatedSegmentCount || 0,
        untranslatedSegmentCount: extra.untranslatedSegmentCount || 0,
        sourceWordCount: extra.sourceWordCount || 0,
        inputTokenCount: extra.inputTokenCount || 0,
        outputTokenCount: extra.outputTokenCount || 0,
        totalTokenCount: extra.totalTokenCount || 0,
        tmHitCount: extra.tmHitCount || 0,
        tmMissCount: extra.tmMissCount || 0,
        confidence: extra.confidence || '',
        warnings: extra.warnings || [],
        createdAt: now,
    };
    const outPath = path.join(cfg.metadataDir, `${safeStem(filePath)}.json`);
    fs.writeFileSync(outPath, `${JSON.stringify(metadata, null, 2)}\n`, 'utf8');
    return outPath;
}