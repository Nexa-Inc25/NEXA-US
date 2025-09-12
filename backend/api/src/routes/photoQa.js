const express = require('express');
const router = express.Router();

// POST /photo/qa — cloud QA → spec refs + fix steps (stub)
router.post('/photo/qa', (req, res) => {
  const { checklist = [], photoKey } = req.body || {};

  const results = (checklist || []).map((item, idx) => ({
    id: item.id || `item-${idx}`,
    passed: idx % 2 === 0, // alternating pass/fail for demo
    message: idx % 2 === 0 ? 'Looks good' : 'Please retake: missing pole tag in frame',
    specRef: 'SPEC-1234'
  }));

  res.json({ photoKey, results, overall: results.every(r => r.passed) ? 'pass' : 'fail' });
});

module.exports = router;
