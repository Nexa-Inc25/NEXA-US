const express = require('express');
const router = express.Router();
const { withOrg } = require('../db');

// POST /closeout/generate — returns PDF S3 key and persists closeout record
router.post('/closeout/generate', async (req, res, next) => {
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
