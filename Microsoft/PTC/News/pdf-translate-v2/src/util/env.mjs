import 'dotenv/config';
import path from 'node:path';
import { normalizeLang, langName, langSuffix, langTag } from './lang.mjs';

function int(value, fallback) {
    const parsed = Number.parseInt(value, 10);
    return Number.isFinite(parsed) ? parsed : fallback;
}

function num(value, fallback) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
}

function bool(value, fallback) {
    if (value == null || value === '') return fallback;
    const normalized = String(value).trim().toLowerCase();
    return ['1', 'true', 'yes', 'y', 'on'].includes(normalized);
}

export function loadConfig(options = {}) {
    const sourceLang = normalizeLang(options.inLang || process.env.SOURCE_LANG || 'en');
    const targetLang = normalizeLang(options.outLang || process.env.TARGET_LANG || 'kr');
    const useAzure = !!process.env.AZURE_OPENAI_API_KEY;

    const cfg = {
        sourceLang,
        targetLang,
        sourceLangName: langName(sourceLang),
        targetLangName: langName(targetLang),
        targetLangTag: langTag(targetLang),
        targetSuffix: langSuffix(targetLang),

        batchSize: int(process.env.BATCH_SIZE, 8),
        maxTokens: int(process.env.MAX_TOKENS, 4096),
        temperature: num(process.env.TEMPERATURE, 0),

        workDir: path.resolve(process.env.WORK_DIR || 'work'),
        inputDir: path.resolve(process.env.INPUT_DIR || 'input'),
        outputDir: path.resolve(process.env.OUTPUT_DIR || 'output'),
        doneDir: path.resolve(process.env.DONE_DIR || 'input/done'),
        tmDbPath: path.resolve(process.env.TM_DB_PATH || 'work/tm.sqlite'),
        glossaryPath: path.resolve(process.env.GLOSSARY_PATH || 'glossary.csv'),

        pdfEngineBin: process.env.PDF_ENGINE_BIN || '',
        pdfFontPath: process.env.PDF_FONT_PATH || '',
        keepOriginalLang: bool(process.env.PDF_KEEP_ORIGINAL_LANG, false),
        keepInput: bool(process.env.PDF_KEEP_INPUT, false) || !!options.keepInput,
        resetTm: !!options.resetTm,

        useAzure,
        openai: {
            apiKey: process.env.OPENAI_API_KEY || '',
            model: process.env.OPENAI_MODEL || 'gpt-4o-mini',
        },
        azure: {
            apiKey: process.env.AZURE_OPENAI_API_KEY || '',
            endpoint: process.env.AZURE_OPENAI_ENDPOINT || '',
            apiVersion: process.env.AZURE_OPENAI_API_VERSION || '2024-08-01-preview',
            deployment: process.env.AZURE_OPENAI_DEPLOYMENT || '',
        },
    };

    cfg.modelLabel = useAzure
        ? `azure:${cfg.azure.deployment || '<unset>'}`
        : `openai:${cfg.openai.model}`;

    return cfg;
}
