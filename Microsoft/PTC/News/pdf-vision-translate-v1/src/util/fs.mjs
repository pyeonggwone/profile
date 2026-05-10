import fs from 'node:fs';
import path from 'node:path';

export function ensureDir(dirPath) {
    fs.mkdirSync(dirPath, { recursive: true });
}

export function readJson(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

export function writeJson(filePath, value) {
    ensureDir(path.dirname(filePath));
    fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

export function pathExists(filePath) {
    return fs.existsSync(filePath);
}

export function removeDir(dirPath) {
    if (fs.existsSync(dirPath)) fs.rmSync(dirPath, { recursive: true, force: true });
}

export function moveFileUnique(source, target) {
    ensureDir(path.dirname(target));
    let finalTarget = target;
    if (fs.existsSync(finalTarget)) {
        const parsed = path.parse(target);
        const stamp = new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14);
        finalTarget = path.join(parsed.dir, `${parsed.name}_${stamp}${parsed.ext}`);
    }
    fs.renameSync(source, finalTarget);
    return finalTarget;
}
