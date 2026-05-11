import fs from 'node:fs';
import path from 'node:path';
import JSZip from 'jszip';

const EXT_TO_FORMAT = new Map([
    ['.epub', 'epub'],
    ['.azw3', 'azw3'],
    ['.mobi', 'mobi'],
    ['.kfx', 'kfx'],
]);

function hasPalmDbHeader(buffer) {
    if (buffer.length < 78) return false;
    const type = buffer.toString('ascii', 60, 68);
    return type === 'BOOKMOBI';
}

function hasMobiHeader(buffer) {
    return buffer.includes(Buffer.from('MOBI', 'ascii'));
}

function hasKfxSignature(buffer) {
    const ascii = buffer.toString('ascii');
    return ascii.includes('CONTBOUNDARY') || ascii.includes('KFX') || ascii.includes('kindle');
}

async function isEpub(filePath, buffer) {
    if (buffer.toString('ascii', 0, 2) !== 'PK') return false;
    try {
        const zip = await JSZip.loadAsync(fs.readFileSync(filePath));
        return !!zip.file('mimetype') && !!zip.file('META-INF/container.xml');
    } catch {
        return false;
    }
}

export async function detectInput(filePath) {
    const extension = path.extname(filePath).toLowerCase();
    const extensionFormat = EXT_TO_FORMAT.get(extension) || '';
    const buffer = fs.readFileSync(filePath).subarray(0, 8192);
    const warnings = [];
    let signatureFormat = '';

    if (await isEpub(filePath, buffer)) signatureFormat = 'epub';
    else if (hasPalmDbHeader(buffer) && hasMobiHeader(buffer)) signatureFormat = extension === '.azw3' ? 'azw3' : 'mobi';
    else if (hasKfxSignature(buffer)) signatureFormat = 'kfx';

    const format = signatureFormat || extensionFormat;
    if (extensionFormat && signatureFormat && extensionFormat !== signatureFormat) {
        warnings.push(`확장자(${extensionFormat})와 내부 시그니처(${signatureFormat})가 다릅니다.`);
    }

    return {
        filePath,
        extension,
        format,
        supported: !!format && EXT_TO_FORMAT.has(extension),
        confidence: signatureFormat ? 'high' : extensionFormat ? 'extension-only' : 'unknown',
        reason: format ? 'format detected' : 'unsupported format',
        warnings,
    };
}
