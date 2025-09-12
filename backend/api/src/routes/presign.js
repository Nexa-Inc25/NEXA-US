const express = require('express');
const crypto = require('crypto');
const router = express.Router();

// POST /presign/photo — returns S3 PUT URL w/ constraints (stubbed for local dev)
router.post('/presign/photo', (req, res) => {
  const { contentType = 'image/jpeg', size = 0, checksum } = req.body || {};
  const key = `org/${(req.user && req.user.orgId) || 'dev-org'}/photos/${Date.now()}-${crypto.randomUUID()}.jpg`;
  const url = `https://example-s3.local/${key}`;

  res.json({
    key,
    url,
    method: 'PUT',
    headers: {
      'Content-Type': contentType,
      'Content-MD5': checksum || 'dev-checksum'
    },
    constraints: {
      maxSize: 25 * 1024 * 1024,
      allowedContentTypes: ['image/jpeg', 'image/png']
    }
  });
});

module.exports = router;
