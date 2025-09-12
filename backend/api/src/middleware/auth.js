const jwksRsa = require('jwks-rsa');
const { expressjwt: jwt } = require('express-jwt');

function authMiddleware() {
  if (process.env.AUTH_DISABLED === '1') {
    return (req, _res, next) => {
      req.user = {
        sub: 'dev-user',
        orgId: 'dev-org',
        roles: ['admin'],
      };
      next();
    };
  }

  const issuer = process.env.AUTH0_ISSUER_URL || (process.env.AUTH0_DOMAIN ? `https://${process.env.AUTH0_DOMAIN}/` : undefined);
  const audience = process.env.AUTH0_AUDIENCE;
  const jwksUri = process.env.AUTH0_JWKS_URI || (issuer ? `${issuer}.well-known/jwks.json` : undefined);
  const orgClaim = process.env.ORG_ID_CLAIM || 'org_id';
  const rolesClaim = process.env.ROLES_CLAIM || 'roles';

  if (!issuer || !audience || !jwksUri) {
    throw new Error('Auth0 config is missing (AUTH0_ISSUER_URL/AUTH0_DOMAIN, AUTH0_AUDIENCE, AUTH0_JWKS_URI)');
  }

  const checkJwt = jwt({
    secret: jwksRsa.expressJwtSecret({
      cache: true,
      rateLimit: true,
      jwksRequestsPerMinute: 5,
      jwksUri,
    }),
    audience,
    issuer,
    algorithms: ['RS256'],
  });

  return (req, res, next) => {
    checkJwt(req, res, (err) => {
      if (err) return next(err);
      const payload = req.auth || req.user || {};
      const orgId = payload[orgClaim];
      const roles = payload[rolesClaim] || [];
      if (!orgId) {
        const e = new Error('Missing org_id claim');
        e.status = 401;
        return next(e);
      }
      req.user = { ...payload, orgId, roles };
      next();
    });
  };
}

module.exports = { authMiddleware };
