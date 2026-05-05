import fs from 'node:fs';

export async function read(filePath) {
    const buffer = fs.readFileSync(filePath);
    const sample = buffer.subarray(0, Math.min(buffer.length, 65536)).toString('ascii');
    const fragmentHints = (sample.match(/CONTBOUNDARY|kindle|KFX/g) || []).length;
    return {
        skipped: true,
        reason: 'KFX native translation writer is not implemented yet',
        metadata: { fragmentHints },
        warnings: ['KFX adapter는 조사 단계입니다. 현재는 구조 힌트만 기록하고 skip합니다.'],
    };
}

export async function write() {
    throw new Error('KFX writer is not implemented yet');
}
