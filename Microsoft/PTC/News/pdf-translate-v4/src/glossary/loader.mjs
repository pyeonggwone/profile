import fs from 'node:fs';
import { parse } from 'csv-parse/sync';

export function loadGlossary(filePath) {
    if (!fs.existsSync(filePath)) return { rows: [], protectedTerms: [] };
    const text = fs.readFileSync(filePath, 'utf8').replace(/^\uFEFF/, '');
    const records = parse(text, { columns: true, skip_empty_lines: true, trim: true });
    const rows = [];
    const protectedTerms = [];
    for (const record of records) {
        const term = (record.term || '').trim();
        if (!term) continue;
        const translation = (record.translation || '').trim();
        const isProtected = ['1', 'true', 'yes'].includes(String(record.protected || '').trim().toLowerCase());
        rows.push({ term, translation, protected: isProtected });
        if (isProtected) protectedTerms.push(term);
    }
    return { rows, protectedTerms };
}

export function glossaryPrompt(rows) {
    if (!rows.length) return '(none)';
    return rows.map((row) => `- ${row.term} => ${row.translation || row.term}${row.protected ? ' (protected, keep exactly)' : ''}`).join('\n');
}
