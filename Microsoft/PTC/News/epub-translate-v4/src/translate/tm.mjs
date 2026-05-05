import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import Database from 'better-sqlite3';

let currentDb = null;
let currentPath = null;

function open(dbPath) {
    if (currentDb && currentPath === dbPath) return currentDb;
    if (currentDb) {
        try { currentDb.close(); } catch { /* ignore */ }
    }
    fs.mkdirSync(path.dirname(dbPath), { recursive: true });
    const db = new Database(dbPath);
    db.pragma('journal_mode = WAL');
    db.exec(`
        CREATE TABLE IF NOT EXISTS tm (
            src_hash TEXT PRIMARY KEY,
            src TEXT NOT NULL,
            tgt TEXT NOT NULL,
            model TEXT,
            source_lang TEXT,
            target_lang TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    `);
    currentDb = db;
    currentPath = dbPath;
    return db;
}

function hashSrc(src, sourceLang, targetLang) {
    return crypto.createHash('sha256').update(`${sourceLang}\n${targetLang}\n${src}`, 'utf8').digest('hex');
}

export function tmGet(dbPath, src, sourceLang, targetLang) {
    const row = open(dbPath).prepare('SELECT tgt FROM tm WHERE src_hash = ?').get(hashSrc(src, sourceLang, targetLang));
    return row ? row.tgt : null;
}

export function tmPut(dbPath, src, tgt, model, sourceLang, targetLang) {
    open(dbPath)
        .prepare('INSERT OR REPLACE INTO tm(src_hash, src, tgt, model, source_lang, target_lang) VALUES (?, ?, ?, ?, ?, ?)')
        .run(hashSrc(src, sourceLang, targetLang), src, tgt, model, sourceLang, targetLang);
}
