import path from 'node:path';

// 입력 PDF 의 stem 만 추출하고, 윈도우 금지 문자를 _ 로 치환한다.
export function safeStem(filePath) {
    return path.basename(filePath, path.extname(filePath))
        .replace(/[<>:"/\\|?*\x00-\x1f]+/g, '_');
}

// `<stem>_<TARGET>.pdf` 출력 경로 규칙.
export function outputPath(outputDir, sourceFilePath, suffix) {
    const stem = safeStem(sourceFilePath);
    return path.join(outputDir, `${stem}_${suffix}.pdf`);
}

// 작업 디렉토리: work/<stem>/
export function workSubdir(workDir, sourceFilePath) {
    return path.join(workDir, safeStem(sourceFilePath));
}
