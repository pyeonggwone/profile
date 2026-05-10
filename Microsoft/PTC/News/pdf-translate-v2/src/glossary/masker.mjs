// 번역 보호용 placeholder 치환기. epub-translate-v5 의 패턴을 그대로 따른다.
// placeholder 형식: __PDFSTR_<KIND>_<NNNN>__ (KIND: URL/EMAIL/VARIABLE/TERM)

const URL_RE = /\bhttps?:\/\/[^\s<>"']+/g;
const EMAIL_RE = /\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b/g;
const VARIABLE_RE = /\{\{[^{}]+\}\}|\{[A-Za-z_][\w.]*\}|\$\{[^}]+\}|<%[^%]+%>/g;

export const PLACEHOLDER_RE = /__PDFSTR_[A-Z]+_\d{4}__/g;

function escapeRegex(value) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export class TokenMasker {
    constructor(protectedTerms = []) {
        this.protectedTerms = [...protectedTerms].sort((a, b) => b.length - a.length);
        this.counter = 0;
    }

    token(kind, value, tokens) {
        this.counter += 1;
        const id = `__PDFSTR_${kind.toUpperCase()}_${String(this.counter).padStart(4, '0')}__`;
        tokens.push({ id, value, kind });
        return id;
    }

    mask(text) {
        const tokens = [];
        let masked = text;
        masked = masked.replace(URL_RE, (match) => this.token('url', match, tokens));
        masked = masked.replace(EMAIL_RE, (match) => this.token('email', match, tokens));
        masked = masked.replace(VARIABLE_RE, (match) => this.token('variable', match, tokens));
        for (const term of this.protectedTerms) {
            if (!term) continue;
            const re = new RegExp(`(?<!\\w)${escapeRegex(term)}(?!\\w)`, 'g');
            masked = masked.replace(re, (match) => this.token('term', match, tokens));
        }
        return { masked, tokens };
    }
}

export function restoreTokens(text, tokens) {
    let out = text;
    for (const token of tokens) out = out.split(token.id).join(token.value);
    return out;
}

export function placeholdersOf(text) {
    return (text.match(PLACEHOLDER_RE) || []).slice().sort();
}

export function placeholdersEqual(a, b) {
    const left = placeholdersOf(a);
    const right = placeholdersOf(b);
    if (left.length !== right.length) return false;
    for (let i = 0; i < left.length; i++) {
        if (left[i] !== right[i]) return false;
    }
    return true;
}
