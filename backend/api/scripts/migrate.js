require('dotenv').config();
const fs = require('fs');
const path = require('path');
const { pool } = require('../src/db');

async function ensureMigrationsTable(client) {
  await client.query(`
    CREATE TABLE IF NOT EXISTS public.schema_migrations (
      id TEXT PRIMARY KEY,
      applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
  `);
}

async function appliedMigrations(client) {
  const { rows } = await client.query('SELECT id FROM public.schema_migrations ORDER BY id');
  return new Set(rows.map(r => r.id));
}

async function run() {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    await ensureMigrationsTable(client);

    const dir = path.resolve(__dirname, '../migrations');
    const files = fs.existsSync(dir)
      ? fs.readdirSync(dir).filter(f => f.endsWith('.sql')).sort()
      : [];

    const applied = await appliedMigrations(client);

    for (const file of files) {
      const id = path.basename(file, '.sql');
      if (applied.has(id)) continue;
      const sql = fs.readFileSync(path.join(dir, file), 'utf8');
      console.log(`Applying migration ${id}...`);
      await client.query(sql);
      await client.query('INSERT INTO public.schema_migrations (id) VALUES ($1)', [id]);
      console.log(`Applied ${id}`);
    }

    await client.query('COMMIT');
    console.log('Migrations complete');
  } catch (err) {
    await client.query('ROLLBACK');
    console.error('Migration failed:', err);
    process.exitCode = 1;
  } finally {
    client.release();
    await pool.end();
  }
}

run();
