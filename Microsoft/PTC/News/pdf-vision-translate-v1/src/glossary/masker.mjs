const URL_RE = /\bhttps?:\/\/[^\s<>"']+/g;
const EMAIL_RE = /\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b/g;
const VARIABLE_RE = /\{\{[^{}]+\}\}|\{[A-Za-z_][\w.]*\}|\$\{[^}]+\}|<%[^%]+%>/g;

function escapeRegex(value) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export class TokenMasker {
    constructor(protectedTerms = []) {
        this.protectedTerms = [...protectedTerms].filter(Boolean).sort((a, b) => b.length - a.length);
        this.counter = 0;
    }

    token(kind, value, tokens) {
        this.counter += 1;
        const id = `__PT_${String(this.counter).padStart(4, '0')}__`;
        tokens.push({ id, value, kind });
        return id;
    }

    mask(text) {
        const tokens = [];
        let masked = String(text || '');
        masked = masked.replace(URL_RE, (match) => this.token('url', match, tokens));
        masked = masked.replace(EMAIL_RE, (match) => this.token('email', match, tokens));
        masked = masked.replace(VARIABLE_RE, (match) => this.token('variable', match, tokens));
        for (const term of this.protectedTerms) {
            const re = new RegExp(`(?<!\\w)${escapeRegex(term)}(?!\\w)`, 'g');
            masked = masked.replace(re, (match) => this.token('term', match, tokens));
        }
        return { masked, tokens };
    }
}

export function restoreTokens(text, tokens) {
    let out = String(text || '');
    for (const token of tokens) out = out.split(token.id).join(token.value);
    return out;
}
