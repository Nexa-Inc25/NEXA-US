const express = require('express');
const { randomUUID } = require('crypto');
const router = express.Router();

// POST /notify/crew — templated SMS/iMessage via SES/SNS gateway (stub)
router.post('/notify/crew', (req, res) => {
  const { jobId, message, pins = [] } = req.body || {};
  const id = randomUUID();
  res.json({ id, jobId, delivered: true, summary: { message, pinsCount: pins.length } });
});

module.exports = router;
