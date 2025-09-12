const express = require('express');
const router = express.Router();

// POST /timesheet/normalize — to utility format (stub)
router.post('/timesheet/normalize', (req, res) => {
  const { crew = [], hours = {}, equipment = [], tasks = [] } = req.body || {};
  const normalized = {
    utility: 'Utility X',
    rows: crew.map(member => ({
      worker: member,
      hours: hours[member] || 8,
      tasks: tasks.slice(0, 2)
    })),
    equipment
  };
  res.json({ normalized, format: 'csv', csv: 'worker,hours\nAlice,8\nBob,8' });
});

module.exports = router;
