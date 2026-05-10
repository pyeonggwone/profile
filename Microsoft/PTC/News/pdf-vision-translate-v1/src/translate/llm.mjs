import OpenAI, { AzureOpenAI } from 'openai';
import { readJson, writeJson } from '../util/fs.mjs';
import { loadGlossary, glossaryPrompt } from '../glossary/loader.mjs';
import { TokenMasker, restoreTokens } from '../glossary/masker.mjs';
import { glossaryHash, tmGet, tmPut } from '../tm/store.mjs';

function clientFor(cfg) {
    if (cfg.provider === 'azure') {
        return new AzureOpenAI({ apiKey: cfg.azure.apiKey, endpoint: cfg.azure.endpoint, apiVersion: cfg.azure.apiVersion, deployment: cfg.azure.translateDeployment });
    }
    if (!cfg.openaiApiKey) throw new Error('OPENAI_API_KEY 가 필요합니다.');
    return new OpenAI({ apiKey: cfg.openaiApiKey });
}

function modelFor(cfg) {
    return cfg.provider === 'azure' ? cfg.azure.translateDeployment : cfg.openaiTranslateModel;
}

function parseJsonArray(text) {
    const trimmed = String(text || '').trim().replace(/^```json\s*/i, '').replace(/^```\s*/i, '').replace(/```$/i, '').trim();
    return JSON.parse(trimmed);
}

async function translateBatch(client, cfg, items, glossaryRows) {
    const response = await client.chat.completions.create({
        model: modelFor(cfg),
        temperature: 0,
        messages: [
            {
                role: 'system',
                content: `Translate from ${cfg.sourceLangName} to ${cfg.targetLangName}. Preserve placeholders exactly. Preserve product names, URLs, IDs, code, and glossary protected terms. Return JSON array only with id and translatedText.\nGlossary:\n${glossaryPrompt(glossaryRows)}`,
            },
            { role: 'user', content: JSON.stringify(items.map((item) => ({ id: item.id, text: item.maskedText })), null, 2) },
        ],
    });
    const content = response.choices?.[0]?.message?.content || '[]';
    const rows = parseJsonArray(content);
    const usage = response.usage || {};
    return { rows, usage: { inputTokens: usage.prompt_tokens || 0, outputTokens: usage.completion_tokens || 0, totalTokens: usage.total_tokens || 0 } };
}

export async function translateSegments(cfg, segmentsJson, outJson) {
    const input = readJson(segmentsJson);
    const glossary = loadGlossary(cfg.glossaryPath);
    const hash = glossaryHash(glossary.rows);
    const masker = new TokenMasker(glossary.protectedTerms);
    const translated = [];
    const misses = [];
    const usage = { tmHit: 0, tmMiss: 0, inputTokens: 0, outputTokens: 0, totalTokens: 0 };

    for (const segment of input.segments || []) {
        const cached = tmGet(cfg.tmDbPath, cfg.sourceLang, cfg.targetLang, segment.text, hash);
        if (cached) {
            usage.tmHit += 1;
            translated.push({ ...segment, sourceText: segment.text, translatedText: cached });
            continue;
        }
        const masked = masker.mask(segment.text);
        misses.push({ ...segment, maskedText: masked.masked, tokens: masked.tokens });
    }

    usage.tmMiss = misses.length;
    if (misses.length) {
        const client = clientFor(cfg);
        for (let index = 0; index < misses.length; index += 20) {
            const batch = misses.slice(index, index + 20);
            const result = await translateBatch(client, cfg, batch, glossary.rows);
            usage.inputTokens += result.usage.inputTokens;
            usage.outputTokens += result.usage.outputTokens;
            usage.totalTokens += result.usage.totalTokens;
            const map = new Map(result.rows.map((row) => [row.id, row.translatedText]));
            for (const item of batch) {
                const raw = map.get(item.id);
                if (!raw) throw new Error(`번역 결과 누락: ${item.id}`);
                const restored = restoreTokens(raw, item.tokens);
                tmPut(cfg.tmDbPath, cfg.sourceLang, cfg.targetLang, item.text, restored, hash);
                translated.push({ ...item, sourceText: item.text, translatedText: restored });
            }
        }
    }

    translated.sort((a, b) => (a.page - b.page) || String(a.id).localeCompare(String(b.id)));
    const output = { source: input.source, sourceLang: cfg.sourceLang, targetLang: cfg.targetLang, segments: translated, usage };
    writeJson(outJson, output);
    return output;
}
