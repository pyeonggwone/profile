import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { PDFDocument } from 'pdf-lib';
import { ensureDir, pathExists, readJson, writeJson } from '../util/fs.mjs';
import { pageImagePath } from '../util/paths.mjs';

function commandExists(command) {
    const probe = process.platform === 'win32'
        ? spawnSync('where', [command], { encoding: 'utf8' })
        : spawnSync('sh', ['-lc', `command -v ${command}`], { encoding: 'utf8' });
    return probe.status === 0;
}

function pngSize(filePath) {
    const buffer = fs.readFileSync(filePath);
    if (buffer.length < 24 || buffer.toString('ascii', 1, 4) !== 'PNG') {
        throw new Error(`PNG 파일이 아닙니다: ${filePath}`);
    }
    return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
}

async function pdfPageSizes(pdfPath) {
    const bytes = fs.readFileSync(pdfPath);
    const doc = await PDFDocument.load(bytes, { ignoreEncryption: true });
    return doc.getPages().map((page, index) => {
        const size = page.getSize();
        return { page: index + 1, widthPt: size.width, heightPt: size.height, rotation: page.getRotation().angle || 0 };
    });
}

function run(command, args) {
    const result = spawnSync(command, args, { encoding: 'utf8' });
    if (result.status !== 0) {
        throw new Error(`${command} 실패: ${(result.stderr || result.stdout || '').trim()}`);
    }
}

async function renderWithPyMuPDF(cfg, paths) {
    const scriptPath = path.join(path.dirname(fileURLToPath(import.meta.url)), 'pymupdf_render.py');
    run(cfg.pythonBin, [scriptPath, paths.source, paths.pagesDir, String(cfg.renderDpi), paths.pagesJson]);
    return readJson(paths.pagesJson);
}

async function renderWithPdftoppm(cfg, paths) {
    const pageSizes = await pdfPageSizes(paths.source);
    const prefix = path.join(paths.pagesDir, 'page');
    run('pdftoppm', ['-png', '-r', String(cfg.renderDpi), paths.source, prefix]);
    const pages = [];
    for (const size of pageSizes) {
        const generated = path.join(paths.pagesDir, `page-${size.page}.png`);
        const target = pageImagePath(paths, size.page);
        if (!pathExists(generated)) throw new Error(`pdftoppm 산출물 없음: ${generated}`);
        fs.renameSync(generated, target);
        const dim = pngSize(target);
        pages.push({ ...size, image: target, widthPx: dim.width, heightPx: dim.height });
    }
    const out = { source: paths.source, dpi: cfg.renderDpi, format: 'png', renderer: 'pdftoppm', pages };
    writeJson(paths.pagesJson, out);
    return out;
}

async function renderWithMutool(cfg, paths) {
    const pageSizes = await pdfPageSizes(paths.source);
    const pattern = path.join(paths.pagesDir, 'page-%03d.png');
    run('mutool', ['draw', '-r', String(cfg.renderDpi), '-o', pattern, paths.source]);
    const pages = [];
    for (const size of pageSizes) {
        const target = pageImagePath(paths, size.page);
        if (!pathExists(target)) throw new Error(`mutool 산출물 없음: ${target}`);
        const dim = pngSize(target);
        pages.push({ ...size, image: target, widthPx: dim.width, heightPx: dim.height });
    }
    const out = { source: paths.source, dpi: cfg.renderDpi, format: 'png', renderer: 'mutool', pages };
    writeJson(paths.pagesJson, out);
    return out;
}

export async function renderPdfPages(cfg, paths) {
    if (pathExists(paths.pagesJson) && !cfg.resetWork) return readJson(paths.pagesJson);
    ensureDir(paths.pagesDir);

    const preferred = cfg.renderer;
    if ((preferred === 'pdftoppm' || preferred === 'auto') && commandExists('pdftoppm')) {
        return renderWithPdftoppm(cfg, paths);
    }
    if ((preferred === 'mutool' || preferred === 'auto') && commandExists('mutool')) {
        return renderWithMutool(cfg, paths);
    }
    return renderWithPyMuPDF(cfg, paths);
}
