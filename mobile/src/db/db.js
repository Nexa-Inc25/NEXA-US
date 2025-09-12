import * as SQLite from 'expo-sqlite/legacy';

export const db = SQLite.openDatabase('nexa_mvp.db');

export function initDb() {
  db.transaction(tx => {
    tx.executeSql(`CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY NOT NULL, name TEXT NOT NULL, profit_chip TEXT NOT NULL, updated_at TEXT NOT NULL)`);
    tx.executeSql(`CREATE TABLE IF NOT EXISTS materials (id TEXT PRIMARY KEY NOT NULL, job_id TEXT NOT NULL, sku TEXT NOT NULL, qty INTEGER NOT NULL, updated_at TEXT NOT NULL)`);
    tx.executeSql(`CREATE TABLE IF NOT EXISTS pins (id TEXT PRIMARY KEY NOT NULL, job_id TEXT NOT NULL, kind TEXT NOT NULL, lat REAL NOT NULL, lng REAL NOT NULL, updated_at TEXT NOT NULL)`);
    tx.executeSql(`CREATE TABLE IF NOT EXISTS checklist (id TEXT PRIMARY KEY NOT NULL, prompt TEXT NOT NULL, required INTEGER NOT NULL, updated_at TEXT NOT NULL)`);
    tx.executeSql(`CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY NOT NULL, value TEXT NOT NULL)`);
  });
}

export function setCursor(key, value) {
  db.transaction(tx => {
    tx.executeSql(`INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)`, [key, value]);
  });
}

export function getCursor(key, cb) {
  db.transaction(tx => {
    tx.executeSql(`SELECT value FROM meta WHERE key = ?`, [key], (_, { rows }) => {
      cb(rows.length ? rows.item(0).value : null);
    });
  });
}

export function upsertTable(name, rows) {
  db.transaction(tx => {
    for (const r of rows) {
      switch (name) {
        case 'jobs':
          tx.executeSql(`INSERT OR REPLACE INTO jobs (id, name, profit_chip, updated_at) VALUES (?, ?, ?, ?)`, [r.id, r.name, r.profit_chip, r.updated_at]);
          break;
        case 'materials':
          tx.executeSql(`INSERT OR REPLACE INTO materials (id, job_id, sku, qty, updated_at) VALUES (?,?,?,?,?)`, [r.id, r.job_id, r.sku, r.qty, r.updated_at]);
          break;
        case 'pins':
          tx.executeSql(`INSERT OR REPLACE INTO pins (id, job_id, kind, lat, lng, updated_at) VALUES (?,?,?,?,?,?)`, [r.id, r.job_id, r.kind, r.lat, r.lng, r.updated_at]);
          break;
        case 'checklist':
          tx.executeSql(`INSERT OR REPLACE INTO checklist (id, prompt, required, updated_at) VALUES (?,?,?,?)`, [r.id, r.prompt, r.required ? 1 : 0, r.updated_at]);
          break;
        default:
          break;
      }
    }
  });
}

export function readJobs(cb) {
  db.transaction(tx => {
    tx.executeSql(`SELECT id, name, profit_chip FROM jobs ORDER BY updated_at DESC`, [], (_, { rows }) => cb(rows._array || []));
  });
}
