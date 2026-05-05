import fs from 'node:fs';

export function readPalmHeader(filePath) {
    const buffer = fs.readFileSync(filePath);
    if (buffer.length < 78) throw new Error('PalmDB header가 너무 짧습니다.');
    const name = buffer.toString('ascii', 0, 32).replace(/\0+$/, '').trim();
    const type = buffer.toString('ascii', 60, 68);
    const recordCount = buffer.readUInt16BE(76);
    const records = [];
    for (let i = 0; i < recordCount; i++) {
        const pos = 78 + i * 8;
        if (pos + 8 > buffer.length) break;
        const offset = buffer.readUInt32BE(pos);
        const nextOffset = i + 1 < recordCount && pos + 16 <= buffer.length ? buffer.readUInt32BE(pos + 8) : buffer.length;
        records.push({ index: i, offset, length: Math.max(0, nextOffset - offset) });
    }
    return { buffer, name, type, recordCount, records };
}

export function isLikelyDrmProtected(buffer) {
    const ascii = buffer.subarray(0, Math.min(buffer.length, 65536)).toString('ascii');
    return /DRMION|DRM|EBOK/i.test(ascii) && /kindle/i.test(ascii);
}
