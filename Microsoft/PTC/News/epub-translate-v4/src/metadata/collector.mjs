import path from 'node:path';

export function createBaseMetadata(filePath, cfg, startedAt) {
    return {
        schemaVersion: '1.0',
        sourceFile: path.basename(filePath),
        outputFile: '',
        format: '',
        title: '',
        authors: [],
        publisher: '',
        language: '',
        targetLanguage: cfg.targetLangTag,
        totalWordCount: 0,
        translatedSegmentCount: 0,
        skippedSegmentCount: 0,
        tmHitCount: 0,
        tmMissCount: 0,
        inputTokenCount: 0,
        outputTokenCount: 0,
        totalTokenCount: 0,
        model: cfg.modelLabel,
        startedAt: startedAt.toISOString(),
        finishedAt: '',
        durationMs: 0,
        status: 'running',
        reason: '',
        warnings: [],
    };
}

export function finishMetadata(metadata, startedAt, status) {
    const finishedAt = new Date();
    return {
        ...metadata,
        status,
        finishedAt: finishedAt.toISOString(),
        durationMs: finishedAt.getTime() - startedAt.getTime(),
    };
}

export function markSkipped(metadata, reason) {
    const startedAt = new Date(metadata.startedAt);
    return { ...finishMetadata(metadata, startedAt, 'skipped'), reason };
}

export function markFailed(metadata, reason, startedAt) {
    return { ...finishMetadata(metadata, startedAt, 'failed'), reason };
}
