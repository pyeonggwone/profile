import OpenAI from 'openai';
import { AzureOpenAI } from 'openai';
import { glossaryPrompt } from './glossary.mjs';

const BLOCK_RE = /^===\s*(\d+)\s*===\s*$/gm;

function buildClient(cfg) {
    if (cfg.useAzure) {
        if (!cfg.azure.apiKey || !cfg.azure.endpoint || !cfg.azure.deployment) {
            throw new Error('AZURE_OPENAI_API_KEY / ENDPOINT / DEPLOYMENT 가 필요합니다.');
        }
        return new AzureOpenAI({
            apiKey: cfg.azure.apiKey,
            endpoint: cfg.azure.endpoint,
            apiVersion: cfg.azure.apiVersion,
            deployment: cfg.azure.deployment,
        });
    }
    if (!cfg.openai.apiKey) throw new Error('OPENAI_API_KEY 가 필요합니다.');
    return new OpenAI({ apiKey: cfg.openai.apiKey });
}

function modelName(cfg) {
    return cfg.useAzure ? cfg.azure.deployment : cfg.openai.model;
}

function buildSystem(cfg, glossaryRows) {
    return `You are a professional EPUB book translator.
Translate from ${cfg.sourceLangName} to ${cfg.targetLangName}.
Return only numbered blocks in the EXACT same === N === format.
Do NOT add JSON, commentary, markdown fences, or explanations.
Preserve every placeholder matching __EPUBSTR_*_0000__ EXACTLY.
Do not translate URLs, emails, variables, or protected glossary terms.
Keep punctuation, inline whitespace, and sentence count similar to the source.
Glossary:
${glossaryPrompt(glossaryRows)}
`;
}

function parseBlocks(text, expected) {
    const matches = [...text.matchAll(BLOCK_RE)];
    if (matches.length !== expected) return null;
    const out = [];
    for (let i = 0; i < matches.length; i++) {
        if (Number.parseInt(matches[i][1], 10) !== i + 1) return null;
        const start = matches[i].index + matches[i][0].length;
        const end = i + 1 < matches.length ? matches[i + 1].index : text.length;
        out.push(text.slice(start, end).replace(/^\s*\n/, '').replace(/\s+$/, ''));
    }
    return out;
}

export async function translateBatch(items, cfg, glossaryRows) {
    const client = buildClient(cfg);
    const model = modelName(cfg);
    const userLines = [];
    items.forEach((item, index) => {
        userLines.push(`=== ${index + 1} ===`);
        userLines.push(item.text);
    });

    const resp = await client.chat.completions.create({
        model,
        temperature: cfg.temperature,
        max_tokens: cfg.maxTokens,
        messages: [
            { role: 'system', content: buildSystem(cfg, glossaryRows) },
            { role: 'user', content: userLines.join('\n') },
        ],
    });
    const content = resp?.choices?.[0]?.message?.content || '';
    const parsed = parseBlocks(content, items.length);
    if (!parsed) throw new Error('LLM 응답 === N === 블록 파싱 실패');
    const usage = resp?.usage || {};
    return {
        texts: parsed,
        usage: {
            inputTokens: usage.prompt_tokens || 0,
            outputTokens: usage.completion_tokens || 0,
            totalTokens: usage.total_tokens || 0,
        },
    };
}