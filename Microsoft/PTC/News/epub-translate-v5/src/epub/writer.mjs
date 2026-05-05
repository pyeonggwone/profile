import fs from 'node:fs';
import path from 'node:path';

export async function writeEpub(zip, outPath) {
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    const mimetypeEntry = zip.files.mimetype;
    if (mimetypeEntry) {
        const content = await mimetypeEntry.async('string');
        delete zip.files.mimetype;
        zip.file('mimetype', content, { compression: 'STORE' });
        const ordered = { mimetype: zip.files.mimetype };
        for (const [name, file] of Object.entries(zip.files)) {
            if (name !== 'mimetype') ordered[name] = file;
        }
        zip.files = ordered;
    }

    const buffer = await zip.generateAsync({
        type: 'nodebuffer',
        compression: 'DEFLATE',
        compressionOptions: { level: 6 },
        mimeType: 'application/epub+zip',
    });
    fs.writeFileSync(outPath, buffer);
}

export async function replaceTextEntry(zip, entryPath, content) {
    zip.file(entryPath, content);
}