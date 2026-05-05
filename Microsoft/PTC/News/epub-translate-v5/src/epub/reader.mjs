import fs from 'node:fs';
import path from 'node:path';
import JSZip from 'jszip';
import { XMLParser, XMLBuilder } from 'fast-xml-parser';

const xmlParser = new XMLParser({
    ignoreAttributes: false,
    attributeNamePrefix: '@_',
    preserveOrder: false,
    trimValues: false,
    parseAttributeValue: false,
});

const xmlBuilder = new XMLBuilder({
    ignoreAttributes: false,
    attributeNamePrefix: '@_',
    format: false,
    suppressEmptyNode: false,
});

export async function loadEpub(filePath) {
    return JSZip.loadAsync(fs.readFileSync(filePath));
}

export function isDrmProtected(zip) {
    return Object.prototype.hasOwnProperty.call(zip.files, 'META-INF/encryption.xml');
}

export async function readContainer(zip) {
    const entry = zip.file('META-INF/container.xml');
    if (!entry) throw new Error('META-INF/container.xml 이 없습니다 (유효한 EPUB 아님)');
    const xml = await entry.async('string');
    const parsed = xmlParser.parse(xml);
    const rootfiles = parsed?.container?.rootfiles?.rootfile;
    const rootfile = Array.isArray(rootfiles) ? rootfiles[0] : rootfiles;
    if (!rootfile || !rootfile['@_full-path']) throw new Error('container.xml 에서 rootfile full-path 를 찾지 못했습니다.');
    return { opfPath: rootfile['@_full-path'] };
}

function asArray(value) {
    if (value == null) return [];
    return Array.isArray(value) ? value : [value];
}

export async function readOpf(zip, opfPath) {
    const entry = zip.file(opfPath);
    if (!entry) throw new Error(`OPF 파일이 없습니다: ${opfPath}`);
    const xml = await entry.async('string');
    const parsed = xmlParser.parse(xml);
    const pkg = parsed?.package;
    if (!pkg) throw new Error('OPF: <package> 누락');

    const manifestItems = asArray(pkg.manifest?.item).map((item) => ({
        id: item['@_id'],
        href: item['@_href'],
        mediaType: item['@_media-type'],
        properties: item['@_properties'] || '',
    }));
    const idToHref = new Map(manifestItems.map((item) => [item.id, item.href]));
    const idToMedia = new Map(manifestItems.map((item) => [item.id, item.mediaType]));
    const spineRefs = asArray(pkg.spine?.itemref).map((ref) => ({
        idref: ref['@_idref'],
        linear: (ref['@_linear'] || 'yes') !== 'no',
    }));
    const opfDir = path.posix.dirname(opfPath);
    const join = (href) => (opfDir && opfDir !== '.' ? path.posix.join(opfDir, href) : href);
    const xhtmlPaths = [];

    for (const ref of spineRefs) {
        const href = idToHref.get(ref.idref);
        const media = idToMedia.get(ref.idref);
        if (!href) continue;
        if (media === 'application/xhtml+xml' || media === 'text/html' || /\.x?html?$/i.test(href)) xhtmlPaths.push(join(href));
    }

    return { opfPath, opfDir, rawXml: xml, parsed, manifestItems, spineRefs, xhtmlPaths };
}

export function setOpfLanguage(opfXml, langTag) {
    return opfXml.replace(/(<(?:\w+:)?language[^>]*>)([\s\S]*?)(<\/(?:\w+:)?language>)/i, `$1${langTag}$3`);
}

export { xmlParser, xmlBuilder };