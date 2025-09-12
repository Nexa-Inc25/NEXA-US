const express = require('express');
const router = express.Router();

// POST /auth/token — In production, this would be handled by Auth0 OIDC flow.
// For local dev, if AUTH_DISABLED=1, we return a mock token payload.
router.post('/auth/token', (req, res) => {
  if (process.env.AUTH_DISABLED === '1') {
    return res.json({
      access_token: 'dev-mock-token',
      token_type: 'Bearer',
      expires_in: 3600,
      payload: {
        sub: 'dev-user',
        org_id: 'dev-org',
        roles: ['admin'],
      },
    });
  }
  res.status(501).json({ error: 'Auth0 OIDC token exchange should be performed client-side.' });
});

module.exports = router;
