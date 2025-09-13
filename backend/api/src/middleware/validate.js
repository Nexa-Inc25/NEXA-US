const { ZodError } = require('zod');

function formatZodError(err) {
  return err.issues.map((i) => ({ path: i.path.join('.'), message: i.message, code: i.code }));
}

function validateBody(schema) {
  return (req, res, next) => {
    try {
      req.body = schema.parse(req.body ?? {});
      next();
    } catch (e) {
      if (e instanceof ZodError) {
        return res.status(400).json({ error: 'Invalid request body', details: formatZodError(e) });
      }
      next(e);
    }
  };
}

function validateQuery(schema) {
  return (req, res, next) => {
    try {
      req.query = schema.parse(req.query ?? {});
      next();
    } catch (e) {
      if (e instanceof ZodError) {
        return res.status(400).json({ error: 'Invalid query', details: formatZodError(e) });
      }
      next(e);
    }
  };
}

module.exports = { validateBody, validateQuery };
