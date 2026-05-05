import 'dotenv/config';
import path from 'node:path';

const LANG_NAME = {
    en: 'English',
    ko: 'Korean',
    kr: 'Korean',
    ja: 'Japanese',
    jp: 'Japanese',
    zh: 'Chinese',
    ch: 'Chinese',
};

const LANG_SUFFIX = {
    en: 'EN',
    ko: 'KR',
    kr: 'KR',
    ja: 'JP',
    jp: 'JP',
    zh: 'CH',
    ch: 'CH',
};

const LANG_TAG = {
    en: 'en',
    ko: 'ko',
    kr: 'ko',
    ja: 'ja',
    jp: 'ja',
    zh: 'zh',
    ch: 'zh',
};

function normalizeLang(value) {
    return String(value || '').trim().toLowerCase();
}

function int(value, fallback) {
    const parsed = Number.parseInt(value, 10);
    return Number.isFinite(parsed) ? parsed : fallback;
}

function num(value, fallback) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
}

export function loadConfig(options = {}) {
    const sourceLang = normalizeLang(process.env.SOURCE_LANG || 'en');
    const targetLang = normalizeLang(process.env.TARGET_LANG || 'kr');
    const useAzure = !!process.env.AZURE_OPENAI_API_KEY;
    const inputPath = path.resolve(options.input || process.env.INPUT_DIR || 'input');
    const outputDir = path.resolve(options.output || process.env.OUTPUT_DIR || 'output');
    const metadataDir = path.resolve(options.metadata || process.env.METADATA_DIR || 'ebook-metadata');
    const onlyFormat = options.format ? String(options.format).toLowerCase() : '';

    const cfg = {
        sourceLang,
        targetLang,
        sourceLangName: LANG_NAME[sourceLang] || sourceLang,
        targetLangName: LANG_NAME[targetLang] || targetLang,
        targetLangTag: LANG_TAG[targetLang] || targetLang,
        targetSuffix: LANG_SUFFIX[targetLang] || targetLang.toUpperCase(),
        batchSize: int(process.env.BATCH_SIZE, 8),
        maxTokens: int(process.env.MAX_TOKENS, 4096),
        temperature: num(process.env.TEMPERATURE, 0),
        inputPath,
        inputDir: path.resolve(process.env.INPUT_DIR || 'input'),
        outputDir,
        metadataDir,
        workDir: path.resolve(process.env.WORK_DIR || 'work'),
        doneDir: path.resolve(process.env.DONE_DIR || 'input/done'),
        tmDbPath: path.resolve(process.env.TM_DB_PATH || 'work/tm.sqlite'),
        glossaryPath: path.resolve(process.env.GLOSSARY_PATH || 'glossary.csv'),
        onlyFormat,
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

    cfg.modelLabel = useAzure ? `azure:${cfg.azure.deployment}` : `openai:${cfg.openai.model}`;
    return cfg;
}
