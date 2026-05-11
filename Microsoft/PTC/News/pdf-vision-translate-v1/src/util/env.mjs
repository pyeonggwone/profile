import 'dotenv/config';
import path from 'node:path';
import { normalizeLang, langName, langSuffix, langTag } from './lang.mjs';

function int(value, fallback) {
    const parsed = Number.parseInt(value, 10);
    return Number.isFinite(parsed) ? parsed : fallback;
}

function chooseDetail(value) {
    const detail = String(value || 'high').trim().toLowerCase();
    if (!['low', 'high', 'original', 'auto'].includes(detail)) {
        throw new Error(`OPENAI_IMAGE_DETAIL 값이 잘못되었습니다: ${value}`);
    }
    return detail;
}

export function loadConfig(options = {}) {
    const provider = String(process.env.LLM_PROVIDER || 'openai').trim().toLowerCase();
    const sourceLang = normalizeLang(options.inLang || process.env.SOURCE_LANG || 'en');
    const targetLang = normalizeLang(options.outLang || process.env.TARGET_LANG || 'kr');
    const imageDetail = chooseDetail(options.detail || process.env.OPENAI_IMAGE_DETAIL || 'high');
    const outputSuffix = String(process.env.PDF_OUTPUT_SUFFIX || langSuffix(targetLang)).trim() || langSuffix(targetLang);

    if (!['openai', 'azure'].includes(provider)) {
        throw new Error(`LLM_PROVIDER 값이 잘못되었습니다: ${provider}`);
    }

    const cfg = {
        provider,
        sourceLang,
        targetLang,
        sourceLangName: langName(sourceLang),
        targetLangName: langName(targetLang),
        targetLangTag: langTag(targetLang),
        outputSuffix,
        openaiApiKey: process.env.OPENAI_API_KEY || '',
        openaiVisionModel: process.env.OPENAI_VISION_MODEL || 'gpt-4.1',
        openaiTranslateModel: process.env.OPENAI_TRANSLATE_MODEL || 'gpt-4.1-mini',
        imageDetail,
        renderDpi: int(options.dpi || process.env.PDF_RENDER_DPI, 300),
        renderFormat: String(process.env.PDF_RENDER_FORMAT || 'png').trim().toLowerCase(),
        renderer: String(process.env.PDF_RENDERER || 'auto').trim().toLowerCase(),
        pythonBin: process.env.PYTHON_BIN || (process.platform === 'win32' ? 'python' : 'python3'),
        fontPath: process.env.PDF_FONT_PATH || '',
        inputDir: path.resolve(process.env.INPUT_DIR || 'input'),
        outputDir: path.resolve(process.env.OUTPUT_DIR || 'output'),
        workDir: path.resolve(process.env.WORK_DIR || 'work'),
        tmDbPath: path.resolve(process.env.TM_DB_PATH || 'work/tm.sqlite'),
        glossaryPath: path.resolve(process.env.GLOSSARY_PATH || 'glossary.csv'),
        resetWork: !!options.resetWork,
        resetTm: !!options.resetTm,
        debug: !!options.debug,
        azure: {
            endpoint: process.env.AZURE_OPENAI_ENDPOINT || '',
            apiKey: process.env.AZURE_OPENAI_API_KEY || '',
            apiVersion: process.env.AZURE_OPENAI_API_VERSION || '2024-08-01-preview',
            visionDeployment: process.env.AZURE_OPENAI_VISION_DEPLOYMENT || '',
            translateDeployment: process.env.AZURE_OPENAI_TRANSLATE_DEPLOYMENT || '',
        },
    };

    if (cfg.provider === 'azure') {
        const hasAnyAzureValue = cfg.azure.endpoint || cfg.azure.apiKey || cfg.azure.visionDeployment || cfg.azure.translateDeployment;
        if (!hasAnyAzureValue) {
            throw new Error('LLM_PROVIDER=azure 이면 Azure OpenAI 환경 변수가 필요합니다.');
        }
    }

    return cfg;
}
