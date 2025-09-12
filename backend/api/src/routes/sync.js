const express = require('express');
const router = express.Router();
const { withOrg } = require('../db');

// GET /sync?since=ISO8601 — delta pull
router.get('/sync', async (req, res, next) => {
  const since = req.query.since || null;
  const now = new Date().toISOString();
  const orgId = (req.user && req.user.orgId) || 'dev-org';

  try {
    const data = await withOrg(orgId, async (client) => {
      const params = [];
      let where = '';
      if (since) {
        params.push(since);
        where = 'WHERE updated_at > $1';
      }

      const [jobs, materials, pins, checklist] = await Promise.all([
        client.query(`SELECT id, name, profit_chip, updated_at FROM public.jobs ${where} ORDER BY updated_at` , params),
        client.query(`SELECT id, job_id, sku, qty, updated_at FROM public.materials ${where} ORDER BY updated_at`, params),
        client.query(`SELECT id, job_id, kind, lat, lng, updated_at FROM public.pins ${where} ORDER BY updated_at`, params),
        client.query(`SELECT id, prompt, required, updated_at FROM public.checklist ${where} ORDER BY updated_at`, params),
      ]);

      return {
        since,
        now,
        jobs: jobs.rows,
        materials: materials.rows,
        pins: pins.rows,
        checklist: checklist.rows,
      };
    });

    res.json(data);
  } catch (err) {
    next(err);
  }
});

// POST /sync — batched upserts
router.post('/sync', async (req, res, next) => {
  const { idempotency_key, upserts } = req.body || {};
  const orgId = (req.user && req.user.orgId) || 'dev-org';

  try {
    const result = await withOrg(orgId, async (client) => {
      const counts = { jobs: 0, materials: 0, pins: 0, checklist: 0 };

      if (upserts && Array.isArray(upserts.jobs)) {
        for (const j of upserts.jobs) {
          await client.query(
            `INSERT INTO public.jobs (id, org_id, name, profit_chip, updated_at)
             VALUES ($1,$2,$3,COALESCE($4,'gray'), COALESCE($5, now()))
             ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, profit_chip=EXCLUDED.profit_chip, updated_at=now()`,
            [j.id, orgId, j.name, j.profit_chip, j.updated_at]
          );
          counts.jobs++;
        }
      }

      if (upserts && Array.isArray(upserts.materials)) {
        for (const m of upserts.materials) {
          await client.query(
            `INSERT INTO public.materials (id, org_id, job_id, sku, qty, updated_at)
             VALUES ($1,$2,$3,$4,$5, COALESCE($6, now()))
             ON CONFLICT (id) DO UPDATE SET job_id=EXCLUDED.job_id, sku=EXCLUDED.sku, qty=EXCLUDED.qty, updated_at=now()`,
            [m.id, orgId, m.job_id, m.sku, m.qty, m.updated_at]
          );
          counts.materials++;
        }
      }

      if (upserts && Array.isArray(upserts.pins)) {
        for (const p of upserts.pins) {
          await client.query(
            `INSERT INTO public.pins (id, org_id, job_id, kind, lat, lng, updated_at)
             VALUES ($1,$2,$3,$4,$5,$6, COALESCE($7, now()))
             ON CONFLICT (id) DO UPDATE SET job_id=EXCLUDED.job_id, kind=EXCLUDED.kind, lat=EXCLUDED.lat, lng=EXCLUDED.lng, updated_at=now()`,
            [p.id, orgId, p.job_id, p.kind, p.lat, p.lng, p.updated_at]
          );
          counts.pins++;
        }
      }

      if (upserts && Array.isArray(upserts.checklist)) {
        for (const c of upserts.checklist) {
          await client.query(
            `INSERT INTO public.checklist (id, org_id, prompt, required, updated_at)
             VALUES ($1,$2,$3, COALESCE($4,true), COALESCE($5, now()))
             ON CONFLICT (id) DO UPDATE SET prompt=EXCLUDED.prompt, required=EXCLUDED.required, updated_at=now()`,
            [c.id, orgId, c.prompt, c.required, c.updated_at]
          );
          counts.checklist++;
        }
      }

      return { counts };
    });

    res.status(202).json({ idempotency_key: idempotency_key || null, accepted: true, ...result });
  } catch (err) {
    next(err);
  }
});

module.exports = router;
