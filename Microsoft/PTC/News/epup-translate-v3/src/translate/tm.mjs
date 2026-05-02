import crypto from 'node:crypto';
import path from 'node:path';
import fs from 'node:fs';
import Database from 'better-sqlite3';

let _db = null;
let _path = null;

function open(dbPath) {
    if (_db && _path === dbPath) return _db;
    if (_db) {
        try { _db.close(); } catch { /* ignore */ }
        _db = null;
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
    _db = db;
    _path = dbPath;
    return db;
}

function hashSrc(src, sourceLang, targetLang) {
    return crypto
        .createHash('sha256')
        .update(`${sourceLang}\n${targetLang}\n${src}`, 'utf8')
        .digest('hex');
}

export function tmGet(dbPath, src, sourceLang, targetLang) {
    const db = open(dbPath);
    const row = db
        .prepare('SELECT tgt FROM tm WHERE src_hash = ?')
        .get(hashSrc(src, sourceLang, targetLang));
    return row ? row.tgt : null;
}

export function tmPut(dbPath, src, tgt, model, sourceLang, targetLang) {
    const db = open(dbPath);
    db.prepare(
        `INSERT OR REPLACE INTO tm(src_hash, src, tgt, model, source_lang, target_lang)
     VALUES (?, ?, ?, ?, ?, ?)`
    ).run(hashSrc(src, sourceLang, targetLang), src, tgt, model, sourceLang, targetLang);
}
