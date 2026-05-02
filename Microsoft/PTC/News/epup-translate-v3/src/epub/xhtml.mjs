import { parse, serialize } from 'parse5';
import { adapter as ADAPTER } from 'parse5-htmlparser2-tree-adapter';

const SKIP_TAGS = new Set([
    'script',
    'style',
    'code',
    'pre',
    'kbd',
    'samp',
    'var',
    'tt',
    'svg',
    'math',
    'noscript',
]);

function isElement(node) {
    return node.type === 'tag' || node.type === 'script' || node.type === 'style';
}

function isText(node) {
    return node.type === 'text';
}

function tagOf(node) {
    return (node.name || '').toLowerCase();
}

function visibleText(node) {
    return node.data || '';
}

function shouldSkipElement(node) {
    const tag = tagOf(node);
    if (SKIP_TAGS.has(tag)) return true;
    // epub:type pagebreak 는 보존
    const epubType = (node.attribs && (node.attribs['epub:type'] || node.attribs.epubtype)) || '';
    if (/\bpagebreak\b/i.test(epubType)) return true;
    return false;
}

/**
 * Parse XHTML chapter and collect translatable text-node references.
 * Returns: { document, segments: [{ id, text, leading, trailing, _node }] }
 */
export function parseChapter(xml) {
    const document = parse(xml, { treeAdapter: ADAPTER, sourceCodeLocationInfo: false });
    const segments = [];
    let counter = 0;

    function walk(node) {
        if (!node) return;
        if (isElement(node)) {
            if (shouldSkipElement(node)) return;
            const children = node.children || [];
            for (const child of children) walk(child);
            return;
        }
        if (isText(node)) {
            const raw = visibleText(node);
            if (!raw) return;
            const trimmed = raw.replace(/\s+/g, ' ').trim();
            if (!trimmed) return;
            // 한글/영문/숫자 문자 하나라도 없으면 스킵 (구두점만)
            if (!/[\p{L}\p{N}]/u.test(trimmed)) return;

            const leadMatch = raw.match(/^\s*/);
            const trailMatch = raw.match(/\s*$/);
            counter += 1;
            segments.push({
                id: counter,
                text: trimmed,
                leading: leadMatch ? leadMatch[0] : '',
                trailing: trailMatch ? trailMatch[0] : '',
                _node: node,
            });
        }
    }

    // walk from document root
    const children = document.children || [];
    for (const c of children) walk(c);
    return { document, segments };
}

export function applyTranslations(document, segments) {
    for (const seg of segments) {
        if (!seg._node || seg.translated == null) continue;
        seg._node.data = `${seg.leading}${seg.translated}${seg.trailing}`;
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
        const children = node.children || [];
        for (const c of children) {
            if (walk(c)) return true;
        }
        return false;
    }
    walk(document);
}

export function serializeChapter(document) {
    return serialize(document, { treeAdapter: ADAPTER });
}
