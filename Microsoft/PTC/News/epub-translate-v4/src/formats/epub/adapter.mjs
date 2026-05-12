import fs from 'node:fs';
import path from 'node:path';
import JSZip from 'jszip';
import { XMLParser } from 'fast-xml-parser';
import { parseChapter, applyTranslations, setHtmlLang, serializeChapter } from './xhtml.mjs';

const xmlParser = new XMLParser({
    ignoreAttributes: false,
    attributeNamePrefix: '@_',
    trimValues: false,
    parseAttributeValue: false,
});

function asArray(value) {
    if (value == null) return [];
    return Array.isArray(value) ? value : [value];
}

async function readContainer(zip) {
    const entry = zip.file('META-INF/container.xml');
    if (!entry) throw new Error('META-INF/container.xml 이 없습니다.');
    const xml = await entry.async('string');
    const parsed = xmlParser.parse(xml);
    const rootfiles = parsed?.container?.rootfiles?.rootfile;
    const rootfile = Array.isArray(rootfiles) ? rootfiles[0] : rootfiles;
    if (!rootfile?.['@_full-path']) throw new Error('container.xml rootfile full-path 누락');
    return rootfile['@_full-path'];
}

async function readOpf(zip, opfPath) {
    const entry = zip.file(opfPath);
    if (!entry) throw new Error(`OPF 파일이 없습니다: ${opfPath}`);
    const rawXml = await entry.async('string');
    const parsed = xmlParser.parse(rawXml);
    const pkg = parsed?.package;
    if (!pkg) throw new Error('OPF package 누락');

    const manifestItems = asArray(pkg.manifest?.item).map((item) => ({
        id: item['@_id'],
        href: item['@_href'],
        mediaType: item['@_media-type'],
    }));
    const idToItem = new Map(manifestItems.map((item) => [item.id, item]));
    const spineRefs = asArray(pkg.spine?.itemref).map((ref) => ref['@_idref']).filter(Boolean);
    const opfDir = path.posix.dirname(opfPath);
    const join = (href) => (opfDir && opfDir !== '.' ? path.posix.join(opfDir, href) : href);
    const xhtmlPaths = [];

    for (const idref of spineRefs) {
        const item = idToItem.get(idref);
        if (!item?.href) continue;
        if (item.mediaType === 'application/xhtml+xml' || item.mediaType === 'text/html' || /\.x?html?$/i.test(item.href)) {
            xhtmlPaths.push(join(item.href));
        }
    }

    const metadata = pkg.metadata || {};
    return {
        rawXml,
        xhtmlPaths,
        metadata: {
            title: metadata['dc:title'] || metadata.title || '',
            language: metadata['dc:language'] || metadata.language || '',
            authors: asArray(metadata['dc:creator'] || metadata.creator).filter((value) => typeof value === 'string'),
            publisher: metadata['dc:publisher'] || metadata.publisher || '',
        },
    };
}

function setOpfLanguage(opfXml, langTag) {
    if (/(<(?:\w+:)?language[^>]*>)([\s\S]*?)(<\/(?:\w+:)?language>)/i.test(opfXml)) {
        return opfXml.replace(/(<(?:\w+:)?language[^>]*>)([\s\S]*?)(<\/(?:\w+:)?language>)/i, `$1${langTag}$3`);
    }
    return opfXml;
}

export async function read(filePath) {
    const zip = await JSZip.loadAsync(fs.readFileSync(filePath));
    if (zip.file('META-INF/encryption.xml')) {
        return { skipped: true, reason: 'DRM protected', metadata: {}, warnings: [] };
    }

    const opfPath = await readContainer(zip);
    const opf = await readOpf(zip, opfPath);
    const chapters = [];
    const segments = [];

    for (const chapterPath of opf.xhtmlPaths) {
        const entry = zip.file(chapterPath);
        if (!entry) continue;
        const xml = await entry.async('string');
        const parsed = parseChapter(xml, chapterPath);
        chapters.push({ path: chapterPath, document: parsed.document, segments: parsed.segments });
        segments.push(...parsed.segments);
    }

    return {
        format: 'epub',
        sourceFile: filePath,
        metadata: opf.metadata,
        segments,
        warnings: [],
        formatState: { zip, opfPath, opfRawXml: opf.rawXml, chapters },
    };
}

export async function write(book, translations, cfg, outPath) {
    const { zip, opfPath, opfRawXml, chapters } = book.formatState;
    const translationMap = new Map(translations.map((item) => [item.segmentId, item.translatedText]));

    for (const chapter of chapters) {
        for (const segment of chapter.segments) {
            if (translationMap.has(segment.id)) segment.translated = translationMap.get(segment.id);
        }
        applyTranslations(chapter.document, chapter.segments);
        setHtmlLang(chapter.document, cfg.targetLangTag);
        zip.file(chapter.path, serializeChapter(chapter.document));
    }

    zip.file(opfPath, setOpfLanguage(opfRawXml, cfg.targetLangTag));
    fs.mkdirSync(path.dirname(outPath), { recursive: true });

    const mimetypeEntry = zip.file('mimetype');
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
