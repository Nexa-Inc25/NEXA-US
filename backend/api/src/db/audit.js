const { withOrg } = require('./index');
const { v4: uuidv4 } = require('uuid');

async function logAudit(orgId, userSub, action, details = {}) {
  const id = `aud-${uuidv4()}`;
  await withOrg(orgId, async (client) => {
    await client.query(
      `INSERT INTO public.audit_log (id, org_id, user_sub, action, details)
       VALUES ($1,$2,$3,$4,$5)`,
      [id, orgId, userSub || null, action, details]
    );
  });
  return id;
}

module.exports = { logAudit };
