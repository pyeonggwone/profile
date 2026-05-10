import fs from 'node:fs';
import path from 'node:path';
import { PDFDocument, StandardFonts, rgb } from 'pdf-lib';
import fontkit from '@pdf-lib/fontkit';
import { normalizedPath } from '../util/paths.mjs';
import { ensureDir, readJson, writeJson } from '../util/fs.mjs';

function hexToRgb(hex, fallback = '#111111') {
    const value = String(hex || fallback).trim();
    const normalized = /^#[0-9a-f]{6}$/i.test(value) ? value : fallback;
    const n = Number.parseInt(normalized.slice(1), 16);
    return rgb(((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255);
}

function maybeWslPath(filePath) {
    const match = String(filePath || '').match(/^([A-Za-z]):[\\/](.*)$/);
    if (!match) return filePath;
    return `/mnt/${match[1].toLowerCase()}/${match[2].replace(/\\/g, '/')}`;
}

function existingFontPath(cfg) {
    const candidates = [cfg.fontPath, maybeWslPath(cfg.fontPath), 'C:/Windows/Fonts/malgun.ttf', '/mnt/c/Windows/Fonts/malgun.ttf', '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'];
    return candidates.find((candidate) => candidate && fs.existsSync(candidate)) || '';
}

function pxToPt(bbox, pageMeta) {
    const x = bbox.x / pageMeta.widthPx * pageMeta.widthPt;
    const y = pageMeta.heightPt - ((bbox.y + bbox.height) / pageMeta.heightPx * pageMeta.heightPt);
    const width = bbox.width / pageMeta.widthPx * pageMeta.widthPt;
    const height = bbox.height / pageMeta.heightPx * pageMeta.heightPt;
    return { x, y, width, height };
}

function fontSizeFor(segment, box) {
    const base = segment.role === 'heading' ? 14 : 10;
    const byHeight = Math.max(5, box.height * 0.55);
    return Math.min(base, byHeight);
}

function wrapText(text, font, fontSize, maxWidth) {
    const value = String(text || '').replace(/\s+/g, ' ').trim();
    if (!value) return [];
    const words = value.includes(' ') ? value.split(' ') : [...value];
    const lines = [];
    let line = '';
    for (const word of words) {
        const next = line ? `${line}${value.includes(' ') ? ' ' : ''}${word}` : word;
        if (font.widthOfTextAtSize(next, fontSize) <= maxWidth || !line) {
            line = next;
        } else {
            lines.push(line);
            line = word;
        }
    }
    if (line) lines.push(line);
    return lines;
}

function drawBoxText(page, font, segment, box, warnings) {
    const padding = Math.min(3, Math.max(1, box.height * 0.08));
    let fontSize = fontSizeFor(segment, box);
    let lines = wrapText(segment.translatedText, font, fontSize, box.width - padding * 2);
    while (fontSize > 5 && lines.length * fontSize * 1.2 > box.height - padding * 2) {
        fontSize -= 0.5;
        lines = wrapText(segment.translatedText, font, fontSize, box.width - padding * 2);
    }
    if (lines.length * fontSize * 1.2 > box.height - padding * 2) warnings.push(`text overflow: ${segment.id}`);

    page.drawRectangle({ x: box.x, y: box.y, width: box.width, height: box.height, color: rgb(1, 1, 1), opacity: 0.92 });
    const color = hexToRgb(segment.color);
    let cursorY = box.y + box.height - padding - fontSize;
    for (const line of lines) {
        if (cursorY < box.y) break;
        page.drawText(line, { x: box.x + padding, y: cursorY, size: fontSize, font, color });
        cursorY -= fontSize * 1.2;
    }
}

export async function composePdf(cfg, paths) {
    const pagesJson = readJson(paths.pagesJson);
    const translated = readJson(paths.translatedJson);
    const byId = new Map((translated.segments || []).map((segment) => [segment.id, segment]));
    const pdfDoc = await PDFDocument.create();
    pdfDoc.registerFontkit(fontkit);

    const fontFile = existingFontPath(cfg);
    const font = fontFile
        ? await pdfDoc.embedFont(fs.readFileSync(fontFile), { subset: true })
        : await pdfDoc.embedFont(StandardFonts.Helvetica);

    const warnings = [];
    const composition = { source: paths.source, target: paths.outputPdf, pages: [] };

    for (const pageMeta of pagesJson.pages) {
        const page = pdfDoc.addPage([pageMeta.widthPt, pageMeta.heightPt]);
        const imageBytes = fs.readFileSync(pageMeta.image);
        const background = await pdfDoc.embedPng(imageBytes);
        page.drawImage(background, { x: 0, y: 0, width: pageMeta.widthPt, height: pageMeta.heightPt });

        const normalized = readJson(normalizedPath(paths, pageMeta.page));
        const operations = [];
        for (const segment of translated.segments || []) {
            if (segment.page !== pageMeta.page) continue;
            const source = segment.sourceBlockId
                ? segment
                : normalized.blocks.find((block) => block.id === segment.id) || segment;
            const box = pxToPt(source.bbox || segment.bbox, pageMeta);
            operations.push({ type: 'text', page: pageMeta.page, sourceId: segment.id, bboxPt: box, text: segment.translatedText, font: fontFile || StandardFonts.Helvetica, fontSize: fontSizeFor(segment, box), color: '#111111', align: 'left' });
            try {
                drawBoxText(page, font, segment, box, warnings);
            } catch (err) {
                warnings.push(`draw failed: ${segment.id}: ${err.message}`);
            }
        }
        composition.pages.push({ page: pageMeta.page, widthPt: pageMeta.widthPt, heightPt: pageMeta.heightPt, backgroundImage: pageMeta.image, operations });
    }

    ensureDir(path.dirname(paths.outputPdf));
    writeJson(paths.compositionJson, composition);
    fs.writeFileSync(paths.outputPdf, await pdfDoc.save());
    return { target: paths.outputPdf, warnings };
}
