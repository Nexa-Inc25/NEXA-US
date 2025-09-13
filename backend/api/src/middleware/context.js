const { v4: uuidv4 } = require('uuid');

function contextMiddleware() {
  return (req, res, next) => {
    const headerId = req.headers['x-request-id'];
    const id = headerId && typeof headerId === 'string' && headerId.trim() ? headerId : uuidv4();
    req.id = id;
    res.setHeader('x-request-id', id);
    next();
  };
}

module.exports = { contextMiddleware };
