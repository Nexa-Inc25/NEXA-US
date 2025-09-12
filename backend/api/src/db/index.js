const { Pool } = require('pg');

const connectionString = process.env.DATABASE_URL || 'postgres://nexa:nexa@localhost:5432/nexa_mvp';

const pool = new Pool({ connectionString, application_name: 'nexa-api' });

async function withClient(fn) {
  const client = await pool.connect();
  try {
    return await fn(client);
  } finally {
    client.release();
  }
}

async function withOrg(orgId, fn) {
  return withClient(async (client) => {
    await client.query('BEGIN');
    // Set org for RLS policies (see current_org_id() in migrations)
    // Use set_config to safely set custom GUC with parameter
    await client.query("SELECT set_config('app.current_org_id', $1, true)", [orgId]);
    try {
      const result = await fn(client);
      await client.query('COMMIT');
      return result;
    } catch (err) {
      await client.query('ROLLBACK');
      throw err;
    }
  });
}

module.exports = { pool, withClient, withOrg };
