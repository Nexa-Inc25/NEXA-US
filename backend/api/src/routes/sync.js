const express = require('express');
const router = express.Router();

// GET /sync?since=ISO8601 — delta pull
router.get('/sync', (req, res) => {
  const since = req.query.since || null;
  const now = new Date().toISOString();
  const demoUpdatedAt = since || now;

  res.json({
    since,
    now,
    jobs: [
      { id: 'job-1', name: 'Pole replacement - Maple St', updated_at: demoUpdatedAt },
      { id: 'job-2', name: 'Transformer upgrade - Oak Ave', updated_at: demoUpdatedAt }
    ],
    materials: [
      { id: 'mat-1', job_id: 'job-1', sku: '#4 clamp', qty: 2, updated_at: demoUpdatedAt }
    ],
    pins: [
      { id: 'pin-1', job_id: 'job-1', type: 'staging', lat: 37.7749, lng: -122.4194, updated_at: demoUpdatedAt }
    ],
    checklist: [
      { id: 'pole_tag', prompt: 'Capture pole tag & insulator in frame', required: true, updated_at: demoUpdatedAt },
      { id: 'guy_anchor', prompt: 'Show anchor angle + tag', required: true, updated_at: demoUpdatedAt }
    ]
  });
});

// POST /sync — batched upserts
router.post('/sync', (req, res) => {
  const { idempotency_key, upserts } = req.body || {};
  const counts = Object.fromEntries(
    Object.entries(upserts || {}).map(([k, arr]) => [k, Array.isArray(arr) ? arr.length : 0])
  );
  res.status(202).json({
    idempotency_key: idempotency_key || null,
    accepted: true,
    counts
  });
});

module.exports = router;
