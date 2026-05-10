import fs from 'node:fs';
import { parse } from 'csv-parse/sync';

export function loadGlossary(filePath) {
    if (!fs.existsSync(filePath)) return { rows: [], protectedTerms: [] };
    const text = fs.readFileSync(filePath, 'utf8').replace(/^\uFEFF/, '');
    const records = parse(text, { columns: true, skip_empty_lines: true, trim: true });
    const rows = [];
    const protectedTerms = [];
    for (const record of records) {
        const source = (record.source || record.term || '').trim();
        if (!source) continue;
        const target = (record.target || record.translation || '').trim();
        const isProtected = ['1', 'true', 'yes', 'y'].includes(String(record.protected || '').trim().toLowerCase());
        const row = { source, target, protected: isProtected };
        rows.push(row);
        if (isProtected) protectedTerms.push(source);
    }
    return { rows, protectedTerms };
}

export function glossaryPrompt(rows) {
    if (!rows.length) return '(none)';
    return rows.map((row) => `- ${row.source} => ${row.target || row.source}${row.protected ? ' (protected, keep exactly)' : ''}`).join('\n');
}
