const express = require('express');
const router = express.Router();
const { withOrg } = require('../db');
const { logAudit } = require('../db/audit');
const crypto = require('crypto');
const rateLimit = require('express-rate-limit');
const { z } = require('zod');
const { validateBody, validateQuery } = require('../middleware/validate');

// Per-route limiter for /sync
const syncWindowMs = parseInt(process.env.RATE_LIMIT_WINDOW_MS_SYNC || process.env.RATE_LIMIT_WINDOW_MS || '60000', 10);
const syncMax = parseInt(process.env.RATE_LIMIT_MAX_SYNC || '120', 10);
const syncLimiter = rateLimit({ windowMs: syncWindowMs, max: syncMax, standardHeaders: true, legacyHeaders: false });

// Validation schemas
const SyncGetQuery = z.object({
  since: z.string().datetime().optional(),
});

const Job = z.object({ id: z.string().min(1), name: z.string().min(1), profit_chip: z.string().optional(), updated_at: z.string().optional() });
const Material = z.object({ id: z.string().min(1), job_id: z.string().min(1), sku: z.string().min(1), qty: z.number().int(), updated_at: z.string().optional() });
const Pin = z.object({ id: z.string().min(1), job_id: z.string().min(1), kind: z.string().min(1), lat: z.number(), lng: z.number(), updated_at: z.string().optional() });
const Check = z.object({ id: z.string().min(1), prompt: z.string().min(1), required: z.boolean().default(true), updated_at: z.string().optional() });
const Upserts = z.object({ jobs: z.array(Job).optional(), materials: z.array(Material).optional(), pins: z.array(Pin).optional(), checklist: z.array(Check).optional() });
const SyncPostBody = z.object({ idempotency_key: z.string().min(1).max(128).optional(), upserts: Upserts.default({}) });

// GET /sync?since=ISO8601 — delta pull
router.get('/sync', syncLimiter, validateQuery(SyncGetQuery), async (req, res, next) => {
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
    // Audit: sync pull
    try {
      await logAudit(orgId, req.user?.sub, 'sync.pull', {
        since,
        counts: {
          jobs: data.jobs.length,
          materials: data.materials.length,
          pins: data.pins.length,
          checklist: data.checklist.length,
        },
      });
    } catch (_e) {
      // best-effort audit
    }
    res.json(data);
  } catch (err) {
    next(err);
  }
});

// POST /sync — batched upserts
router.post('/sync', syncLimiter, validateBody(SyncPostBody), async (req, res, next) => {
  const { idempotency_key, upserts } = req.body || {};
  const orgId = (req.user && req.user.orgId) || 'dev-org';

  try {
    const result = await withOrg(orgId, async (client) => {
      // Idempotency check
      if (idempotency_key) {
        const existing = await client.query(
          `SELECT response FROM public.idempotency_keys WHERE id = $1 AND endpoint = 'POST /sync'`,
          [idempotency_key]
        );
        if (existing.rows.length) {
          return { reused: true, ...(existing.rows[0].response || {}) };
        }
      }

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

      const response = { counts };

      // Store idempotency record
      if (idempotency_key) {
        const hash = crypto
          .createHash('sha256')
          .update(JSON.stringify(upserts || {}))
          .digest('hex');
        await client.query(
          `INSERT INTO public.idempotency_keys (id, org_id, endpoint, request_hash, response, status)
           VALUES ($1,$2,'POST /sync',$3,$4,'succeeded')
           ON CONFLICT (id) DO UPDATE SET response = EXCLUDED.response, updated_at = now()`,
          [idempotency_key, orgId, hash, response]
        );
      }

      // Audit: sync push
      try {
        await logAudit(orgId, req.user?.sub, 'sync.push', {
          idempotency_key: idempotency_key || null,
          counts,
        });
      } catch (_e) {
        // best-effort
      }

      return response;
    });

    res.status(202).json({ idempotency_key: idempotency_key || null, accepted: true, ...result });
  } catch (err) {
    next(err);
  }
});

module.exports = router;
