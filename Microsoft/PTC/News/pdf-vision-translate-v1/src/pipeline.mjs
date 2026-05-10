import fs from 'node:fs';
import path from 'node:path';
import { ensureDir, moveFileUnique, pathExists, readJson, removeDir, writeJson } from './util/fs.mjs';
import { buildPaths } from './util/paths.mjs';
import { info, warn } from './util/log.mjs';
import { renderPdfPages } from './render/pdf-to-image.mjs';
import { analyzePages } from './vision/openai-layout.mjs';
import { normalizeAnalysis } from './normalize/layout-normalizer.mjs';
import { translateSegments } from './translate/llm.mjs';
import { composePdf } from './compose/pdf-writer.mjs';
import { tmReset } from './tm/store.mjs';

function listInputPdfs(cfg) {
    ensureDir(cfg.inputDir);
    return fs.readdirSync(cfg.inputDir)
        .filter((name) => name.toLowerCase().endsWith('.pdf'))
        .map((name) => path.join(cfg.inputDir, name));
}

function initDirs(cfg) {
    ensureDir(cfg.inputDir);
    ensureDir(path.join(cfg.inputDir, 'done'));
    ensureDir(cfg.outputDir);
    ensureDir(cfg.workDir);
}

async function processOne(cfg, pdfPath) {
    const paths = buildPaths(cfg, pdfPath);
    const startedAt = new Date().toISOString();
    const report = { source: paths.source, target: paths.outputPdf, status: 'running', startedAt, finishedAt: null, pages: 0, segments: 0, warnings: [], usage: { visionInputTokens: 0, visionOutputTokens: 0, translateInputTokens: 0, translateOutputTokens: 0, totalTokens: 0 } };

    try {
        if (cfg.resetWork) removeDir(paths.workRoot);
        ensureDir(paths.workRoot);

        info(`RENDER ${path.basename(paths.source)}`);
        const pages = await renderPdfPages(cfg, paths);
        report.pages = pages.pages.length;

        info(`VISION_ANALYZE ${path.basename(paths.source)}`);
        const visionUsage = await analyzePages(cfg, paths, pages);
        report.usage.visionInputTokens += visionUsage.inputTokens;
        report.usage.visionOutputTokens += visionUsage.outputTokens;

        info(`NORMALIZE ${path.basename(paths.source)}`);
        const normalized = normalizeAnalysis(cfg, paths, pages);
        report.segments = normalized.segments.length;
        report.warnings.push(...normalized.warnings);

        info(`TRANSLATE ${path.basename(paths.source)}`);
        const translated = await translateSegments(cfg, paths.segmentsJson, paths.translatedJson);
        report.usage.translateInputTokens += translated.usage.inputTokens;
        report.usage.translateOutputTokens += translated.usage.outputTokens;

        info(`COMPOSE ${path.basename(paths.source)}`);
        const composed = await composePdf(cfg, paths);
        report.warnings.push(...composed.warnings);

        if (!pathExists(paths.outputPdf)) throw new Error(`출력 PDF 생성 실패: ${paths.outputPdf}`);
        moveFileUnique(paths.source, paths.donePdf);
        report.status = 'success';
        report.finishedAt = new Date().toISOString();
        report.usage.totalTokens = Object.values(report.usage).filter(Number.isFinite).reduce((sum, value) => sum + value, 0);
        writeJson(paths.reportJson, report);
        info(`DONE ${paths.outputPdf}`);
        return report;
    } catch (err) {
        report.status = 'failed';
        report.finishedAt = new Date().toISOString();
        report.error = err?.message || String(err);
        if (cfg.debug && err?.stack) report.stack = err.stack;
        writeJson(paths.reportJson, report);
        warn(`FAILED ${path.basename(paths.source)}: ${report.error}`);
        throw err;
    }
}

export async function runAll(cfg, input) {
    initDirs(cfg);
    if (cfg.resetTm) tmReset(cfg.tmDbPath);
    const files = input ? [path.resolve(input)] : listInputPdfs(cfg);
    if (!files.length) {
        warn(`처리할 PDF가 없습니다: ${cfg.inputDir}`);
        return [];
    }

    const reports = [];
    for (const file of files) reports.push(await processOne(cfg, file));
    return reports;
}

export async function renderCommand(cfg, input) {
    initDirs(cfg);
    const paths = buildPaths(cfg, input);
    if (cfg.resetWork) removeDir(paths.workRoot);
    return renderPdfPages(cfg, paths);
}

export async function analyzeCommand(cfg, input) {
    initDirs(cfg);
    let pagesJsonPath;
    if (fs.statSync(input).isDirectory()) {
        pagesJsonPath = path.resolve(input, '..', 'pages.json');
    } else if (path.basename(input) === 'pages.json') {
        pagesJsonPath = path.resolve(input);
    } else {
        pagesJsonPath = buildPaths(cfg, input).pagesJson;
    }
    const pages = readJson(pagesJsonPath);
    const paths = buildPaths(cfg, pages.source);
    return analyzePages(cfg, paths, pages);
}

export async function translateCommand(cfg, segmentsJson) {
    initDirs(cfg);
    const out = path.join(path.dirname(segmentsJson), 'translated.json');
    return translateSegments(cfg, segmentsJson, out);
}

export async function composeCommand(cfg, inputPdf, translatedJson) {
    initDirs(cfg);
    const paths = buildPaths(cfg, inputPdf);
    paths.translatedJson = path.resolve(translatedJson);
    return composePdf(cfg, paths);
}
