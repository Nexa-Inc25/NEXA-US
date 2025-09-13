const express = require('express');
const router = express.Router();
const { withOrg } = require('../db');
const rateLimit = require('express-rate-limit');
const { z } = require('zod');
const { validateBody } = require('../middleware/validate');

// Per-route limiter for timesheet
const windowMs = parseInt(process.env.RATE_LIMIT_WINDOW_MS_TIMESHEET || process.env.RATE_LIMIT_WINDOW_MS || '60000', 10);
const max = parseInt(process.env.RATE_LIMIT_MAX_TIMESHEET || '60', 10);
const timesheetLimiter = rateLimit({ windowMs, max, standardHeaders: true, legacyHeaders: false });

const TimesheetSchema = z.object({
  crew: z.array(z.string().min(1)).default([]),
  hours: z.record(z.string(), z.number().nonnegative()).default({}),
  equipment: z.array(z.string()).default([]),
  tasks: z.array(z.string()).default([]),
  jobId: z.string().min(1).nullable().optional(),
});

// POST /timesheet/normalize — to utility format (stub)
router.post('/timesheet/normalize', timesheetLimiter, validateBody(TimesheetSchema), async (req, res, next) => {
  const orgId = (req.user && req.user.orgId) || 'dev-org';
  const { crew = [], hours = {}, equipment = [], tasks = [], jobId = null } = req.body || {};

  try {
    const result = await withOrg(orgId, async (client) => {
      const normalized = {
        utility: 'Utility X',
        rows: crew.map(member => ({
          worker: member,
          hours: hours[member] || 8,
          tasks: tasks.slice(0, 2)
        })),
        equipment
      };

      // Simple CSV build
      const csvRows = ['worker,hours'];
      for (const r of normalized.rows) {
        csvRows.push(`${r.worker},${r.hours}`);
      }
      const csv = csvRows.join('\n');

      const id = `ts-${Date.now()}`;
      await client.query(
        `INSERT INTO public.timesheets (id, org_id, job_id, submitted_by, payload)
         VALUES ($1,$2,$3,$4,$5)
         ON CONFLICT (id) DO UPDATE SET payload = EXCLUDED.payload, updated_at = now()`,
        [id, orgId, jobId, (req.user && req.user.sub) || 'dev-user', { normalized, csv }]
      );

      return { id, normalized, format: 'csv', csv };
    });

    res.json(result);
  } catch (err) {
    next(err);
  }
});

module.exports = router;
