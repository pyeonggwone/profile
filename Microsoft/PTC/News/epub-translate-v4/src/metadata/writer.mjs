import fs from 'node:fs';
import path from 'node:path';

function safeStem(fileName) {
    return path.basename(fileName, path.extname(fileName)).replace(/[<>:"/\\|?*]+/g, '_');
}

export async function writeBookMetadata(metadata, cfg) {
    fs.mkdirSync(cfg.metadataDir, { recursive: true });
    const filePath = path.join(cfg.metadataDir, `${safeStem(metadata.sourceFile)}.json`);
    fs.writeFileSync(filePath, `${JSON.stringify(metadata, null, 2)}\n`, 'utf8');
    return filePath;
}
