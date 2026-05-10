import fs from 'node:fs';
import OpenAI, { AzureOpenAI } from 'openai';
import { analysisPath } from '../util/paths.mjs';
import { pathExists, writeJson } from '../util/fs.mjs';
import { pageLayoutSchema } from './schema.mjs';

function clientFor(cfg) {
    if (cfg.provider === 'azure') {
        return new AzureOpenAI({ apiKey: cfg.azure.apiKey, endpoint: cfg.azure.endpoint, apiVersion: cfg.azure.apiVersion, deployment: cfg.azure.visionDeployment });
    }
    if (!cfg.openaiApiKey) throw new Error('OPENAI_API_KEY 가 필요합니다.');
    return new OpenAI({ apiKey: cfg.openaiApiKey });
}

function modelFor(cfg) {
    return cfg.provider === 'azure' ? cfg.azure.visionDeployment : cfg.openaiVisionModel;
}

function outputText(response) {
    if (response.output_text) return response.output_text;
    const chunks = [];
    for (const item of response.output || []) {
        for (const content of item.content || []) {
            if (content.type === 'output_text' && content.text) chunks.push(content.text);
        }
    }
    return chunks.join('\n');
}

async function analyzeOne(cfg, client, pageMeta, outPath) {
    const imageBytes = fs.readFileSync(pageMeta.image);
    const imageUrl = `data:image/png;base64,${imageBytes.toString('base64')}`;
    const prompt = `Extract all page layout objects for PDF reconstruction.
Use pixel coordinates from the top-left of the image.
Return every visible text block.
Return text blocks, tables, images, captions, headers, footers, page numbers, reading order, and approximate visual styles.
Return table cells with row, column, spans, bbox, text, alignment, background, and border.
Return images with bbox, description, and containsText.
Return confidence and warnings.
Set page=${pageMeta.page}, width=${pageMeta.widthPx}, height=${pageMeta.heightPx}, dpi=${pageMeta.dpi || 300}, rotation=${pageMeta.rotation || 0}.
Do not translate. Do not summarize. Do not omit small text unless unreadable.`;

    let lastErr;
    for (let attempt = 1; attempt <= 3; attempt++) {
        try {
            const response = await client.responses.create({
                model: modelFor(cfg),
                input: [{
                    role: 'user',
                    content: [
                        { type: 'input_text', text: prompt },
                        { type: 'input_image', image_url: imageUrl, detail: cfg.imageDetail },
                    ],
                }],
                text: { format: { type: 'json_schema', ...pageLayoutSchema } },
            });
            const text = outputText(response);
            const parsed = JSON.parse(text);
            writeJson(outPath, parsed);
            const usage = response.usage || {};
            return { inputTokens: usage.input_tokens || 0, outputTokens: usage.output_tokens || 0 };
        } catch (err) {
            lastErr = err;
            if (attempt === 3) break;
        }
    }
    throw lastErr;
}

export async function analyzePages(cfg, paths, pagesJson) {
    const client = clientFor(cfg);
    const usage = { inputTokens: 0, outputTokens: 0 };
    for (const page of pagesJson.pages) {
        const outPath = analysisPath(paths, page.page);
        if (pathExists(outPath) && !cfg.resetWork) continue;
        const pageUsage = await analyzeOne(cfg, client, { ...page, dpi: pagesJson.dpi }, outPath);
        usage.inputTokens += pageUsage.inputTokens;
        usage.outputTokens += pageUsage.outputTokens;
    }
    return usage;
}
