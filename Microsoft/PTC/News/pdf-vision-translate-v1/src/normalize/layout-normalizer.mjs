import { analysisPath, normalizedPath } from '../util/paths.mjs';
import { readJson, writeJson } from '../util/fs.mjs';

function clamp(value, min, max) {
    return Math.max(min, Math.min(max, Number(value) || 0));
}

function normalizeBbox(bbox, width, height) {
    const x = clamp(bbox?.x, 0, width);
    const y = clamp(bbox?.y, 0, height);
    const w = clamp(bbox?.width, 0, width - x);
    const h = clamp(bbox?.height, 0, height - y);
    return { x, y, width: w, height: h };
}

function isSkippableText(text) {
    const value = String(text || '').trim();
    if (!value) return true;
    if (/^\d+$/.test(value)) return true;
    if (/^https?:\/\//i.test(value)) return true;
    if (/^[\w.+-]+@[\w-]+(?:\.[\w-]+)+$/.test(value)) return true;
    return false;
}

function stableBlockId(page, index) {
    return `p${page}-b${String(index + 1).padStart(3, '0')}`;
}

export function normalizeAnalysis(cfg, paths, pagesJson) {
    const allSegments = [];
    const warnings = [];
    const normalizedPages = [];

    for (const pageMeta of pagesJson.pages) {
        const analysis = readJson(analysisPath(paths, pageMeta.page));
        const blocks = (analysis.blocks || []).map((block, index) => {
            const normalized = {
                ...block,
                id: block.id || stableBlockId(pageMeta.page, index),
                page: pageMeta.page,
                type: block.type || 'unknown',
                role: block.role || '',
                bbox: normalizeBbox(block.bbox, pageMeta.widthPx, pageMeta.heightPx),
                readingOrder: block.readingOrder ?? null,
                confidence: Number.isFinite(block.confidence) ? block.confidence : 0,
            };
            if (normalized.confidence < 0.6) warnings.push(`low confidence: ${normalized.id}`);
            return normalized;
        }).sort((a, b) => {
            const left = a.readingOrder ?? 999999;
            const right = b.readingOrder ?? 999999;
            if (left !== right) return left - right;
            if (Math.abs(a.bbox.y - b.bbox.y) > 8) return a.bbox.y - b.bbox.y;
            return a.bbox.x - b.bbox.x;
        });

        blocks.forEach((block, index) => {
            block.readingOrder = block.readingOrder ?? index + 1;
            if (block.type === 'text' && !isSkippableText(block.text)) {
                allSegments.push({ id: block.id, page: pageMeta.page, kind: 'text', text: block.text, bbox: block.bbox, role: block.role });
            }
            if (block.type === 'table' && block.table?.cells?.length) {
                for (const cell of block.table.cells) {
                    if (isSkippableText(cell.text)) continue;
                    allSegments.push({ id: `${block.id}-r${cell.row}c${cell.column}`, page: pageMeta.page, kind: 'table-cell', text: cell.text, bbox: normalizeBbox(cell.bbox, pageMeta.widthPx, pageMeta.heightPx), role: 'table-cell', sourceBlockId: block.id, row: cell.row, column: cell.column });
                }
            }
        });

        const normalized = { ...analysis, page: pageMeta.page, width: pageMeta.widthPx, height: pageMeta.heightPx, dpi: pagesJson.dpi, rotation: pageMeta.rotation, blocks, warnings: [...(analysis.warnings || [])] };
        writeJson(normalizedPath(paths, pageMeta.page), normalized);
        normalizedPages.push(normalized);
    }

    const segmentsJson = { source: paths.source, sourceLang: cfg.sourceLang, targetLang: cfg.targetLang, segments: allSegments };
    writeJson(paths.segmentsJson, segmentsJson);
    return { pages: normalizedPages, segments: allSegments, warnings };
}
