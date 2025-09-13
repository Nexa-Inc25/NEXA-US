const express = require('express');
const crypto = require('crypto');
const { createPresignedPost } = require('@aws-sdk/s3-presigned-post');
const { createS3Client } = require('../services/s3');
const rateLimit = require('express-rate-limit');
const { z } = require('zod');
const { validateBody } = require('../middleware/validate');
const router = express.Router();

// Per-route rate limit (stricter for presign)
const presignWindowMs = parseInt(process.env.RATE_LIMIT_WINDOW_MS_PRESIGN || process.env.RATE_LIMIT_WINDOW_MS || '60000', 10);
const presignMax = parseInt(process.env.RATE_LIMIT_MAX_PRESIGN || '30', 10);
const presignLimiter = rateLimit({ windowMs: presignWindowMs, max: presignMax, standardHeaders: true, legacyHeaders: false });

// Validation schema for request body
const PhotoSchema = z.object({
  contentType: z.enum(['image/jpeg', 'image/png']).default('image/jpeg'),
  size: z.number().int().nonnegative().optional(),
});

// POST /presign/photo — returns S3 presigned POST with constraints
router.post('/presign/photo', presignLimiter, validateBody(PhotoSchema), async (req, res, next) => {
  const orgId = (req.user && req.user.orgId) || 'dev-org';
  const { contentType = 'image/jpeg', size = 0 } = req.body || {};

  try {
    const allowed = (process.env.PRESIGN_ALLOWED_TYPES || 'image/jpeg,image/png')
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    if (!allowed.includes(contentType)) {
      return res.status(400).json({ error: 'Unsupported content type', allowed });
    }

    const maxMb = parseInt(process.env.PRESIGN_MAX_MB || '25', 10);
    const maxBytes = maxMb * 1024 * 1024;
    if (size && Number(size) > maxBytes) {
      return res.status(400).json({ error: 'File too large', maxBytes });
    }

    const bucket = process.env.S3_BUCKET;
    if (!bucket) {
      return res.status(500).json({ error: 'S3_BUCKET is not configured' });
    }

    const ext = contentType === 'image/png' ? 'png' : 'jpg';
    const key = `org/${orgId}/photos/${Date.now()}-${crypto.randomUUID()}.${ext}`;

    // If AWS creds are not present, return a dev stub to unblock local testing
    if (!process.env.AWS_ACCESS_KEY_ID || !process.env.AWS_SECRET_ACCESS_KEY) {
      const stubUrl = `${process.env.AWS_S3_ENDPOINT || 'https://example-s3.local'}/${bucket}/${key}`;
      return res.json({
        dev_stub: true,
        key,
        url: stubUrl,
        method: 'PUT',
        headers: { 'Content-Type': contentType },
        constraints: { maxSize: maxBytes, allowedContentTypes: allowed },
      });
    }

    const s3 = createS3Client();
    const fields = { 'Content-Type': contentType }; // enforce exact content-type
    // Optional server-side encryption
    if (process.env.S3_KMS_KEY_ID) {
      fields['x-amz-server-side-encryption'] = 'aws:kms';
      fields['x-amz-server-side-encryption-aws-kms-key-id'] = process.env.S3_KMS_KEY_ID;
    }

    const conditions = [
      ['content-length-range', 1, maxBytes],
      { 'Content-Type': contentType },
    ];

    const { url, fields: postFields } = await createPresignedPost(s3, {
      Bucket: bucket,
      Key: key,
      Conditions: conditions,
      Fields: fields,
      Expires: 60, // seconds
    });

    res.json({
      key,
      url,
      method: 'POST',
      fields: postFields,
      constraints: { maxSize: maxBytes, allowedContentTypes: allowed },
    });
  } catch (err) {
    next(err);
  }
});

module.exports = router;
