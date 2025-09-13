const express = require('express');
const router = express.Router();
const { withOrg } = require('../db');
const rateLimit = require('express-rate-limit');
const { z } = require('zod');
const { validateBody } = require('../middleware/validate');

// Per-route limiter (fallbacks to global envs if specific not provided)
const windowMs = parseInt(process.env.RATE_LIMIT_WINDOW_MS_CLOSEOUT || process.env.RATE_LIMIT_WINDOW_MS || '60000', 10);
const max = parseInt(process.env.RATE_LIMIT_MAX_CLOSEOUT || '30', 10);
const closeoutLimiter = rateLimit({ windowMs, max, standardHeaders: true, legacyHeaders: false });

const CloseoutSchema = z.object({
  jobId: z.string().min(1).nullable().optional(),
  approve: z.boolean().optional().default(false),
});

// POST /closeout/generate — returns PDF S3 key and persists closeout record
router.post('/closeout/generate', closeoutLimiter, validateBody(CloseoutSchema), async (req, res, next) => {
  const orgId = (req.user && req.user.orgId) || 'dev-org';
  const { jobId = null, approve = false } = req.body || {};
  const pdfKey = `org/${orgId}/closeouts/${jobId || 'job'}/${Date.now()}.pdf`;
  const shareLink = approve ? `https://example-s3.local/${pdfKey}` : null;

  try {
    const result = await withOrg(orgId, async (client) => {
      const id = `co-${Date.now()}`;
      await client.query(
        `INSERT INTO public.closeouts (id, org_id, job_id, pdf_key, approved)
         VALUES ($1,$2,$3,$4,$5)
         ON CONFLICT (id) DO UPDATE SET pdf_key = EXCLUDED.pdf_key, approved = EXCLUDED.approved, updated_at = now()`,
        [id, orgId, jobId, pdfKey, !!approve]
      );
      return { id, jobId, pdfKey, approved: !!approve, shareLink };
    });
    res.json(result);
  } catch (err) {
    next(err);
  }
});

module.exports = router;
