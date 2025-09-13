const express = require('express');
const rateLimit = require('express-rate-limit');
const { z } = require('zod');
const { validateQuery } = require('../middleware/validate');
const { withOrg } = require('../db');

const router = express.Router();

// Per-route limiter for admin audit listing
const windowMs = parseInt(process.env.RATE_LIMIT_WINDOW_MS_ADMIN || process.env.RATE_LIMIT_WINDOW_MS || '60000', 10);
const max = parseInt(process.env.RATE_LIMIT_MAX_ADMIN || '60', 10);
const adminLimiter = rateLimit({ windowMs, max, standardHeaders: true, legacyHeaders: false });

const AuditQuery = z.object({
  limit: z.coerce.number().int().min(1).max(200).default(50),
  since: z.string().datetime().optional(),
  cursor: z.string().datetime().optional(), // keyset: fetch items created_at < cursor
  action: z.string().min(1).optional(),
  format: z.enum(['json', 'csv']).default('json'),
});

// GET /admin/audit?limit=50&since=ISO&action=sync.push
router.get('/admin/audit', adminLimiter, validateQuery(AuditQuery), async (req, res, next) => {
  const orgId = (req.user && req.user.orgId) || 'dev-org';
  const { limit, since, cursor, action, format } = req.query;

  try {
    const data = await withOrg(orgId, async (client) => {
      const params = [];
      const conds = [];
      if (since) {
        params.push(since);
        conds.push(`created_at >= $${params.length}`);
      }
      if (cursor) {
        params.push(cursor);
        conds.push(`created_at < $${params.length}`);
      }
      if (action) {
        params.push(action);
        conds.push(`action = $${params.length}`);
      }
      const where = conds.length ? `WHERE ${conds.join(' AND ')}` : '';
      params.push(limit);
      const sql = `SELECT id, user_sub, action, details, created_at FROM public.audit_log ${where}
                   ORDER BY created_at DESC
                   LIMIT $${params.length}`;
      const rows = await client.query(sql, params);
      const items = rows.rows;
      const next_cursor = items.length ? items[items.length - 1].created_at.toISOString?.() || items[items.length - 1].created_at : null;
      return { items, count: rows.rowCount, next_cursor };
    });

    if (format === 'csv') {
      const header = ['id', 'user_sub', 'action', 'created_at', 'details'];
      const lines = [header.join(',')];
      for (const row of data.items) {
        const details = JSON.stringify(row.details || {});
        const created = (row.created_at && row.created_at.toISOString) ? row.created_at.toISOString() : String(row.created_at);
        // naive CSV escaping for commas/quotes by wrapping in quotes and doubling quotes inside
        const esc = (s) => '"' + String(s).replace(/"/g, '""') + '"';
        lines.push([row.id, row.user_sub || '', row.action, created, details].map(esc).join(','));
      }
      res.setHeader('Content-Type', 'text/csv');
      res.setHeader('Content-Disposition', 'attachment; filename="audit.csv"');
      return res.send(lines.join('\n'));
    }

    res.json(data);
  } catch (err) {
    next(err);
  }
});

module.exports = router;
