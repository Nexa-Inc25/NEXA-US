require('dotenv').config();
const { withOrg } = require('../src/db');

const ORG = process.env.SEED_ORG_ID || 'dev-org';

async function seed() {
  await withOrg(ORG, async (client) => {
    console.log(`Seeding data for org ${ORG}...`);
    // Jobs
    await client.query(
      `INSERT INTO public.jobs (id, org_id, name, profit_chip)
       VALUES ($1,$2,$3,$4)
       ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, profit_chip=EXCLUDED.profit_chip, updated_at=now()`,
      ['job-1', ORG, 'Pole replacement - Maple St', 'green']
    );
    await client.query(
      `INSERT INTO public.jobs (id, org_id, name, profit_chip)
       VALUES ($1,$2,$3,$4)
       ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, profit_chip=EXCLUDED.profit_chip, updated_at=now()`,
      ['job-2', ORG, 'Transformer upgrade - Oak Ave', 'gray']
    );

    // Materials
    await client.query(
      `INSERT INTO public.materials (id, org_id, job_id, sku, qty)
       VALUES ($1,$2,$3,$4,$5)
       ON CONFLICT (id) DO UPDATE SET job_id=EXCLUDED.job_id, sku=EXCLUDED.sku, qty=EXCLUDED.qty, updated_at=now()`,
      ['mat-1', ORG, 'job-1', '#4 clamp', 2]
    );

    // Pins
    await client.query(
      `INSERT INTO public.pins (id, org_id, job_id, kind, lat, lng)
       VALUES ($1,$2,$3,$4,$5,$6)
       ON CONFLICT (id) DO UPDATE SET job_id=EXCLUDED.job_id, kind=EXCLUDED.kind, lat=EXCLUDED.lat, lng=EXCLUDED.lng, updated_at=now()`,
      ['pin-1', ORG, 'job-1', 'staging', 37.7749, -122.4194]
    );

    // Checklist
    await client.query(
      `INSERT INTO public.checklist (id, org_id, prompt, required)
       VALUES ($1,$2,$3,$4)
       ON CONFLICT (id) DO UPDATE SET prompt=EXCLUDED.prompt, required=EXCLUDED.required, updated_at=now()`,
      ['pole_tag', ORG, 'Capture pole tag & insulator in frame', true]
    );
    await client.query(
      `INSERT INTO public.checklist (id, org_id, prompt, required)
       VALUES ($1,$2,$3,$4)
       ON CONFLICT (id) DO UPDATE SET prompt=EXCLUDED.prompt, required=EXCLUDED.required, updated_at=now()`,
      ['guy_anchor', ORG, 'Show anchor angle + tag', true]
    );

    console.log('Seed complete.');
  });
}

seed().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
