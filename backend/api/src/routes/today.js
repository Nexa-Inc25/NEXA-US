const express = require('express');
const router = express.Router();
const { withOrg } = require('../db');

// GET /today — sequenced run-of-show for the user
router.get('/today', async (req, res, next) => {
  const user = req.user || { sub: 'dev-user', orgId: 'dev-org' };
  const now = new Date();
  const date = now.toISOString().slice(0, 10);
  try {
    const data = await withOrg(user.orgId, async (client) => {
      const { rows: jobs } = await client.query(
        `SELECT id, name, profit_chip FROM public.jobs ORDER BY updated_at DESC`
      );

      const sequence = [
        { id: 'pretrip', type: 'pre_trip', title: 'Pre-trip', primaryAction: 'Start' },
        ...jobs.map(j => ({ id: `job-${j.id}`, type: 'job', jobId: j.id, title: j.name })),
        { id: 'closeout', type: 'closeout', title: 'Closeout' }
      ];

      return {
        date,
        user: { sub: user.sub, orgId: user.orgId },
        sequence,
        jobs: jobs.map(j => ({ id: j.id, name: j.name, profitChip: j.profit_chip }))
      };
    });
    res.json(data);
  } catch (err) {
    next(err);
  }
});

module.exports = router;
