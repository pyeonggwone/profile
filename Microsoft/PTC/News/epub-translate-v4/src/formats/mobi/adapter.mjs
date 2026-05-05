import { readPalmHeader, isLikelyDrmProtected } from '../kindle/palm.mjs';

export async function read(filePath) {
    const palm = readPalmHeader(filePath);
    const warnings = ['MOBI native writer는 MVP 초안입니다. 현재 단계에서는 구조 분석 후 안전하게 skip합니다.'];
    if (isLikelyDrmProtected(palm.buffer)) {
        return { skipped: true, reason: 'DRM protected', metadata: { title: palm.name }, warnings };
    }
    return {
        skipped: true,
        reason: 'MOBI native translation writer is not implemented yet',
        metadata: { title: palm.name, recordCount: palm.recordCount },
        warnings,
    };
}

export async function write() {
    throw new Error('MOBI writer is not implemented yet');
}
