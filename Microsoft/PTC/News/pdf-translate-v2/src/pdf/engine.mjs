import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { log } from '../util/log.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// src/pdf/engine.mjs 기준으로 프로젝트 루트는 두 단계 위.
const PROJECT_ROOT = path.resolve(__dirname, '..', '..');
// pdf-translate-v1 디렉토리 (형제 디렉토리)
const V1_ROOT = path.resolve(PROJECT_ROOT, '..', 'pdf-translate-v1');

const BIN_NAME = process.platform === 'win32' ? 'pdftr.exe' : 'pdftr';

function firstExisting(candidates) {
    for (const candidate of candidates) {
        if (candidate && fs.existsSync(candidate)) return candidate;
    }
    return '';
}

function whichBin(name) {
    const dirs = (process.env.PATH || '').split(path.delimiter).filter(Boolean);
    for (const dir of dirs) {
        const full = path.join(dir, name);
        if (fs.existsSync(full)) return full;
    }
    return '';
}

let cachedBin = null;

export function resolvePdfEngineBin(cfg) {
    if (cachedBin && fs.existsSync(cachedBin)) return cachedBin;
    const candidates = [
        cfg.pdfEngineBin,
        path.join(PROJECT_ROOT, 'pdf-engine', 'target', 'release', BIN_NAME),
        path.join(PROJECT_ROOT, 'pdf-engine', 'target', 'debug', BIN_NAME),
        path.join(V1_ROOT, 'target', 'release', BIN_NAME),
        path.join(V1_ROOT, 'target', 'debug', BIN_NAME),
    ];
    const found = firstExisting(candidates) || whichBin(BIN_NAME);
    if (!found) {
        throw new Error(
            `pdftr 바이너리를 찾을 수 없습니다. INSTALL.md 5단계를 참조해 빌드한 뒤 PDF_ENGINE_BIN 을 .env 에 지정하세요. 탐색 경로:\n  - ${candidates.filter(Boolean).join('\n  - ')}`,
        );
    }
    cachedBin = found;
    return found;
}

function runEngine(cfg, args, { captureStdout = true } = {}) {
    const bin = resolvePdfEngineBin(cfg);
    return new Promise((resolve, reject) => {
        const child = spawn(bin, args, { stdio: ['ignore', 'pipe', 'pipe'] });
        let stdout = '';
        let stderr = '';
        if (captureStdout) {
            child.stdout.on('data', (chunk) => { stdout += chunk.toString('utf8'); });
        } else {
            child.stdout.on('data', () => { /* drain */ });
        }
        child.stderr.on('data', (chunk) => { stderr += chunk.toString('utf8'); });
        child.on('error', reject);
        child.on('close', (code) => {
            if (code === 0) resolve({ stdout, stderr });
            else reject(new Error(`pdftr ${args[0] || ''} 종료 코드 ${code}: ${(stderr || stdout).trim()}`));
        });
    });
}

// pdftr inspect <pdf> --json
export async function inspect(cfg, pdfPath) {
    const { stdout } = await runEngine(cfg, ['inspect', pdfPath, '--json']);
    return JSON.parse(stdout);
}

// pdftr text <pdf> --json -> v1 PageText[] JSON
// 결과: [{ page, width, height, runs: [{ text, x, y, font_size, font_resource }] }]
export async function extractPages(cfg, pdfPath) {
    const { stdout } = await runEngine(cfg, ['text', pdfPath, '--json']);
    const parsed = JSON.parse(stdout);
    if (!Array.isArray(parsed)) {
        throw new Error('pdftr text --json 응답이 배열이 아닙니다.');
    }
    return parsed;
}

// pdftr edit <input> <output> --edits <edits.json>
export async function applyEdits(cfg, inputPdf, outputPdf, editsJsonPath) {
    fs.mkdirSync(path.dirname(outputPdf), { recursive: true });
    const { stdout, stderr } = await runEngine(cfg, [
        'edit', inputPdf, outputPdf, '--edits', editsJsonPath,
    ]);
    log.debug('pdftr edit:', (stdout || stderr).trim());
    if (!fs.existsSync(outputPdf)) {
        throw new Error(`pdftr edit 실행 후 출력 파일이 생성되지 않았습니다: ${outputPdf}`);
    }
    return outputPdf;
}
