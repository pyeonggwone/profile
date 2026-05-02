import fs from 'node:fs';
import path from 'node:path';

/**
 * Write the EPUB zip preserving:
 *  - mimetype as the FIRST entry, STORED (no compression)
 *  - all other entries DEFLATE
 *  - original file names/paths (we mutate jszip in-place before calling this)
 */
export async function writeEpub(zip, outPath) {
    fs.mkdirSync(path.dirname(outPath), { recursive: true });

    // Ensure mimetype is first & STORED if it exists.
    const files = zip.files;
    const mimetypeEntry = files['mimetype'];
    if (mimetypeEntry) {
        const content = await mimetypeEntry.async('string');
        // Re-add to push to end; we'll rebuild ordering below by removing and re-adding all.
        delete zip.files['mimetype'];
        zip.file('mimetype', content, { compression: 'STORE' });
    }

    // JSZip preserves insertion order on generateAsync. To put mimetype first:
    // rebuild the files dictionary with mimetype first.
    if (mimetypeEntry) {
        const ordered = {};
        ordered['mimetype'] = zip.files['mimetype'];
        for (const [name, file] of Object.entries(zip.files)) {
            if (name === 'mimetype') continue;
            ordered[name] = file;
        }
        zip.files = ordered;
    }

    const buf = await zip.generateAsync({
        type: 'nodebuffer',
        compression: 'DEFLATE',
        compressionOptions: { level: 6 },
        mimeType: 'application/epub+zip',
    });
    fs.writeFileSync(outPath, buf);
}

export async function replaceTextEntry(zip, entryPath, content) {
    const existing = zip.file(entryPath);
    if (!existing) {
        zip.file(entryPath, content);
        return;
    }
    // jszip overwrites when calling .file() with same name
    zip.file(entryPath, content);
}
