import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import Database from 'better-sqlite3';

let currentDb = null;
let currentPath = null;

function open(dbPath) {
    if (currentDb && currentPath === dbPath) return currentDb;
    if (currentDb) currentDb.close();
    fs.mkdirSync(path.dirname(dbPath), { recursive: true });
    const db = new Database(dbPath);
    db.pragma('journal_mode = WAL');
    db.exec(`
    CREATE TABLE IF NOT EXISTS translations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source_lang TEXT NOT NULL,
      target_lang TEXT NOT NULL,
      source_text TEXT NOT NULL,
      translated_text TEXT NOT NULL,
      glossary_hash TEXT NOT NULL,
      created_at TEXT NOT NULL,
      UNIQUE(source_lang, target_lang, source_text, glossary_hash)
    )
  `);
    currentDb = db;
    currentPath = dbPath;
    return db;
}

export function glossaryHash(rows) {
    return crypto.createHash('sha256').update(JSON.stringify(rows || []), 'utf8').digest('hex');
}

export function tmGet(dbPath, sourceLang, targetLang, sourceText, hash) {
    const row = open(dbPath).prepare('SELECT translated_text FROM translations WHERE source_lang = ? AND target_lang = ? AND source_text = ? AND glossary_hash = ?').get(sourceLang, targetLang, sourceText, hash);
    return row?.translated_text || null;
}

export function tmPut(dbPath, sourceLang, targetLang, sourceText, translatedText, hash) {
    open(dbPath).prepare('INSERT OR REPLACE INTO translations(source_lang, target_lang, source_text, translated_text, glossary_hash, created_at) VALUES (?, ?, ?, ?, ?, ?)').run(sourceLang, targetLang, sourceText, translatedText, hash, new Date().toISOString());
}

export function tmReset(dbPath) {
    if (currentDb && currentPath === dbPath) {
        currentDb.close();
        currentDb = null;
        currentPath = null;
    }
    for (const suffix of ['', '-wal', '-shm']) {
        const filePath = `${dbPath}${suffix}`;
        if (fs.existsSync(filePath)) fs.rmSync(filePath, { force: true });
    }
}
