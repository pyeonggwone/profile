import fs from 'node:fs';
import { parse } from 'csv-parse/sync';

export function loadGlossary(filePath) {
    if (!fs.existsSync(filePath)) {
        return { rows: [], protectedTerms: [] };
    }
    const text = fs.readFileSync(filePath, 'utf8').replace(/^\uFEFF/, '');
    const records = parse(text, {
        columns: true,
        skip_empty_lines: true,
        trim: true,
    });
    const rows = [];
    const protectedTerms = [];
    for (const r of records) {
        const term = (r.term || '').trim();
        if (!term) continue;
        const translation = (r.translation || '').trim();
        const isProtected = String(r.protected || '').trim().toLowerCase() === 'true';
        rows.push({ term, translation, protected: isProtected });
        if (isProtected) protectedTerms.push(term);
    }
    return { rows, protectedTerms };
}

export function glossaryPrompt(rows) {
    if (!rows.length) return '(none)';
    return rows
        .map((r) => {
            const suffix = r.protected ? ' (protected, keep exactly)' : '';
            return `- ${r.term} => ${r.translation || r.term}${suffix}`;
        })
        .join('\n');
}
