const express = require('express');
const router = express.Router();

// GET /today — sequenced run-of-show for the user
router.get('/today', (req, res) => {
  const user = req.user || { orgId: 'unknown' };
  const now = new Date();
  const date = now.toISOString().slice(0, 10);

  const data = {
    date,
    user: { sub: user.sub, orgId: user.orgId },
    sequence: [
      { id: 'pretrip', type: 'pre_trip', title: 'Pre-trip', primaryAction: 'Start' },
      { id: 'job-1', type: 'job', jobId: 'job-1', title: 'Job 1' },
      { id: 'job-2', type: 'job', jobId: 'job-2', title: 'Job 2' },
      { id: 'closeout', type: 'closeout', title: 'Closeout' }
    ],
    jobs: [
      { id: 'job-1', name: 'Pole replacement - Maple St', profitChip: 'green' },
      { id: 'job-2', name: 'Transformer upgrade - Oak Ave', profitChip: 'gray' }
    ]
  };

  res.json(data);
});

module.exports = router;
