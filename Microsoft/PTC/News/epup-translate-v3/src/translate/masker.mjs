const URL_RE = /\bhttps?:\/\/[^\s<>"']+/g;
const EMAIL_RE = /\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b/g;
const VARIABLE_RE = /\{\{[^{}]+\}\}|\{[A-Za-z_][\w.]*\}|\$\{[^}]+\}|<%[^%]+%>/g;

export const PLACEHOLDER_RE = /__EPUBSTR_[A-Z]+_\d{4}__/g;

function escapeRegex(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export class TokenMasker {
    constructor(protectedTerms = []) {
        this.protectedTerms = [...protectedTerms].sort((a, b) => b.length - a.length);
        this.counter = 0;
    }

    _token(kind, value, tokens) {
        this.counter += 1;
        const id = `__EPUBSTR_${kind.toUpperCase()}_${String(this.counter).padStart(4, '0')}__`;
        tokens.push({ id, value, kind });
        return id;
    }

    mask(text) {
        const tokens = [];
        let masked = text;
        masked = masked.replace(URL_RE, (m) => this._token('url', m, tokens));
        masked = masked.replace(EMAIL_RE, (m) => this._token('email', m, tokens));
        masked = masked.replace(VARIABLE_RE, (m) => this._token('variable', m, tokens));
        for (const term of this.protectedTerms) {
            if (!term) continue;
            const re = new RegExp(`(?<!\\w)${escapeRegex(term)}(?!\\w)`, 'g');
            masked = masked.replace(re, (m) => this._token('term', m, tokens));
        }
        return { masked, tokens };
    }
}

export function restoreTokens(text, tokens) {
    let out = text;
    for (const t of tokens) {
        out = out.split(t.id).join(t.value);
    }
    return out;
}

export function placeholdersOf(text) {
    return (text.match(PLACEHOLDER_RE) || []).slice().sort();
}

export function placeholdersEqual(a, b) {
    const A = placeholdersOf(a);
    const B = placeholdersOf(b);
    if (A.length !== B.length) return false;
    for (let i = 0; i < A.length; i++) if (A[i] !== B[i]) return false;
    return true;
}
