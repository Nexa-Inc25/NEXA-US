/**
 * Global Error Handler Middleware
 */

const logger = require('../utils/logger');

const errorHandler = (err, req, res, next) => {
    logger.error('Error occurred:', {
        error: err.message,
        stack: err.stack,
        url: req.url,
        method: req.method,
        ip: req.ip,
        user: req.user ? req.user.id : 'anonymous'
    });
    
    // Multer file upload errors
    if (err.code === 'LIMIT_FILE_SIZE') {
        return res.status(413).json({
            error: 'File too large',
            message: `Maximum file size is ${process.env.MAX_UPLOAD_SIZE_MB || 100}MB`,
            code: 'FILE_TOO_LARGE'
        });
    }
    
    // Database errors
    if (err.code && err.code.startsWith('23')) {  // Postgres constraint violations
        return res.status(400).json({
            error: 'Database constraint violation',
            message: 'The request violates a database constraint',
            code: err.code
        });
    }
    
    // Validation errors
    if (err.name === 'ValidationError') {
        return res.status(400).json({
            error: 'Validation failed',
            details: err.details || err.message
        });
    }
    
    // Default error
    const statusCode = err.statusCode || 500;
    const message = err.message || 'Internal server error';
    
    res.status(statusCode).json({
        error: message,
        ...(process.env.NODE_ENV === 'development' && { stack: err.stack }),
        timestamp: new Date().toISOString()
    });
};

module.exports = {
    errorHandler
};
