import { parse, serialize } from 'parse5';
import { adapter as ADAPTER } from 'parse5-htmlparser2-tree-adapter';

const SKIP_TAGS = new Set(['script', 'style', 'code', 'pre', 'kbd', 'samp', 'var', 'tt', 'svg', 'math', 'noscript']);

function isElement(node) {
    return node.type === 'tag' || node.type === 'script' || node.type === 'style';
}

function isText(node) {
    return node.type === 'text';
}

function tagOf(node) {
    return (node.name || '').toLowerCase();
}

function shouldSkipElement(node) {
    const tag = tagOf(node);
    if (SKIP_TAGS.has(tag)) return true;
    const epubType = (node.attribs && (node.attribs['epub:type'] || node.attribs.epubtype)) || '';
    return /\bpagebreak\b/i.test(epubType);
}

export function parseChapter(xml, chapterPath) {
    const document = parse(xml, { treeAdapter: ADAPTER, sourceCodeLocationInfo: false });
    const segments = [];
    let counter = 0;

    function walk(node) {
        if (!node) return;
        if (isElement(node)) {
            if (shouldSkipElement(node)) return;
            for (const child of node.children || []) walk(child);
            return;
        }
        if (!isText(node)) return;
        const raw = node.data || '';
        const trimmed = raw.replace(/\s+/g, ' ').trim();
        if (!trimmed || !/[\p{L}\p{N}]/u.test(trimmed)) return;
        counter += 1;
        segments.push({
            id: `${chapterPath}#${counter}`,
            text: trimmed,
            kind: 'body',
            location: { format: 'epub', path: chapterPath, selector: `text()[${counter}]` },
            leading: raw.match(/^\s*/)?.[0] || '',
            trailing: raw.match(/\s*$/)?.[0] || '',
            _node: node,
        });
    }

    for (const child of document.children || []) walk(child);
    return { document, segments };
}

export function applyTranslations(document, segments) {
    for (const segment of segments) {
        if (!segment._node || segment.translated == null) continue;
        segment._node.data = `${segment.leading}${segment.translated}${segment.trailing}`;
    }
}

export function setHtmlLang(document, langTag) {
    function walk(node) {
        if (!node) return false;
        if (isElement(node) && tagOf(node) === 'html') {
            node.attribs = node.attribs || {};
            node.attribs.lang = langTag;
            node.attribs['xml:lang'] = langTag;
            return true;
        }
        for (const child of node.children || []) {
            if (walk(child)) return true;
        }
        return false;
    }
    walk(document);
}

export function serializeChapter(document) {
    return serialize(document, { treeAdapter: ADAPTER });
}
