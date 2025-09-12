const express = require('express');
const router = express.Router();

// POST /closeout/generate — returns PDF S3 key (stub)
router.post('/closeout/generate', (req, res) => {
  const { jobId, approve = false } = req.body || {};
  const pdfKey = `org/${(req.user && req.user.orgId) || 'dev-org'}/closeouts/${jobId || 'job'}/${Date.now()}.pdf`;
  const shareLink = approve ? `https://example-s3.local/${pdfKey}` : null;
  res.json({ jobId, pdfKey, approved: !!approve, shareLink });
});

module.exports = router;
