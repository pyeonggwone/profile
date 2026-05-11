import { TokenMasker, restoreTokens, placeholdersEqual } from './masker.mjs';
import { tmGet, tmPut } from './tm.mjs';
import { translateBatch } from './llm.mjs';
import { countWords } from '../metadata/word-count.mjs';
import { log } from '../util/log.mjs';

function emptyUsage() {
    return { inputTokens: 0, outputTokens: 0, totalTokens: 0 };
}

function addUsage(total, usage = {}) {
    total.inputTokens += usage.inputTokens || 0;
    total.outputTokens += usage.outputTokens || 0;
    total.totalTokens += usage.totalTokens || 0;
}

export async function translateSegments(segments, cfg, glossary) {
    const masker = new TokenMasker(glossary.protectedTerms);
    const masked = segments.map((segment) => {
        const { masked: text, tokens } = masker.mask(segment.text);
        return { ...segment, maskedText: text, tokens };
    });

    const cache = new Map();
    const misses = [];
    let tmHitCount = 0;
    let tmMissCount = 0;

    for (const item of masked) {
        const cached = tmGet(cfg.tmDbPath, item.maskedText, cfg.sourceLang, cfg.targetLang);
        if (cached != null) {
            tmHitCount += 1;
            cache.set(item.id, cached);
        } else {
            tmMissCount += 1;
            misses.push(item);
        }
    }

    const usage = emptyUsage();
    for (let i = 0; i < misses.length; i += cfg.batchSize) {
        const batch = misses.slice(i, i + cfg.batchSize);
        let outputs;
        try {
            const result = await translateBatch(batch.map((item) => ({ id: item.id, text: item.maskedText })), cfg, glossary.rows);
            outputs = result.texts;
            addUsage(usage, result.usage);
        } catch (err) {
            log.warn(`LLM 배치 실패 (${i}-${i + batch.length}): ${err.message}. 원문 fallback.`);
            outputs = batch.map((item) => item.maskedText);
        }

        for (let j = 0; j < batch.length; j++) {
            const item = batch[j];
            let output = outputs[j];
            let cacheable = true;
            if (!placeholdersEqual(item.maskedText, output)) {
                log.warn(`placeholder 불일치 (${item.id}). 원문 fallback.`);
                output = item.maskedText;
                cacheable = false;
            }
            cache.set(item.id, output);
            if (cacheable) tmPut(cfg.tmDbPath, item.maskedText, output, cfg.modelLabel, cfg.sourceLang, cfg.targetLang);
        }
    }

    const translations = [];
    let skippedSegmentCount = 0;
    for (const item of masked) {
        const translatedMasked = cache.get(item.id);
        if (translatedMasked == null) {
            skippedSegmentCount += 1;
            continue;
        }
        translations.push({
            segmentId: item.id,
            sourceText: item.text,
            translatedText: restoreTokens(translatedMasked, item.tokens),
            tmHit: !misses.some((miss) => miss.id === item.id),
        });
    }

    return {
        translations,
        usage,
        totalWordCount: segments.reduce((sum, segment) => sum + countWords(segment.text), 0),
        translatedSegmentCount: translations.length,
        skippedSegmentCount,
        tmHitCount,
        tmMissCount,
    };
}
