import path from 'node:path';

export function stemOf(pdfPath) {
    return path.basename(pdfPath, path.extname(pdfPath));
}

export function buildPaths(cfg, pdfPath) {
    const source = path.resolve(pdfPath);
    const stem = stemOf(source);
    const workRoot = path.join(cfg.workDir, stem);
    return {
        source,
        stem,
        workRoot,
        pagesDir: path.join(workRoot, 'pages'),
        analysisDir: path.join(workRoot, 'analysis'),
        normalizedDir: path.join(workRoot, 'normalized'),
        pagesJson: path.join(workRoot, 'pages.json'),
        segmentsJson: path.join(workRoot, 'segments.json'),
        translatedJson: path.join(workRoot, 'translated.json'),
        compositionJson: path.join(workRoot, 'composition.json'),
        reportJson: path.join(workRoot, 'report.json'),
        outputPdf: path.join(cfg.outputDir, `${stem}_${cfg.outputSuffix}.pdf`),
        donePdf: path.join(cfg.inputDir, 'done', path.basename(source)),
    };
}

export function pageImagePath(paths, page, ext = 'png') {
    return path.join(paths.pagesDir, `page-${String(page).padStart(3, '0')}.${ext}`);
}

export function analysisPath(paths, page) {
    return path.join(paths.analysisDir, `page-${String(page).padStart(3, '0')}.json`);
}

export function normalizedPath(paths, page) {
    return path.join(paths.normalizedDir, `page-${String(page).padStart(3, '0')}.json`);
}
