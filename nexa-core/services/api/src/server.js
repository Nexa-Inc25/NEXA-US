/**
 * Nexa Core API Service
 * Main server entry point
 */

require('dotenv').config();
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const morgan = require('morgan');
const rateLimit = require('express-rate-limit');

// Import routes
const jobsRouter = require('./routes/jobs');
const submissionsRouter = require('./routes/submissions');
const auditsRouter = require('./routes/audits');
const usersRouter = require('./routes/users');
const healthRouter = require('./routes/health');

// Import middleware
const { errorHandler } = require('./middleware/errorHandler');
const { authMiddleware } = require('./middleware/auth');
const logger = require('./utils/logger');

const app = express();
const PORT = process.env.PORT || 3000;

// ============================================================================
// MIDDLEWARE
// ============================================================================

// Security headers
app.use(helmet());

// CORS
app.use(cors({
    origin: process.env.NODE_ENV === 'production' 
        ? ['https://nexa-dashboard.onrender.com', 'https://nexa.com']
        : '*',
    credentials: true
}));

// Compression
app.use(compression());

// Body parsing
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Logging
if (process.env.NODE_ENV !== 'test') {
    app.use(morgan('combined', { stream: logger.stream }));
}

// Rate limiting
const limiter = rateLimit({
    windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS) || 15 * 60 * 1000, // 15 min
    max: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS) || 100,
    message: 'Too many requests from this IP, please try again later',
    standardHeaders: true,
    legacyHeaders: false
});
app.use('/api', limiter);

// ============================================================================
// ROUTES
// ============================================================================

// Public routes
app.use('/health', healthRouter);

// API routes (authenticated)
app.use('/api/jobs', authMiddleware, jobsRouter);
app.use('/api/submissions', authMiddleware, submissionsRouter);
app.use('/api/audits', authMiddleware, auditsRouter);
app.use('/api/users', authMiddleware, usersRouter);

// Root endpoint
app.get('/', (req, res) => {
    res.json({
        name: 'Nexa Core API',
        version: '1.0.0',
        status: 'operational',
        timestamp: new Date().toISOString(),
        endpoints: {
            health: '/health',
            jobs: '/api/jobs',
            submissions: '/api/submissions',
            audits: '/api/audits',
            users: '/api/users'
        },
        documentation: process.env.ENABLE_SWAGGER_DOCS === 'true' ? '/api/docs' : null
    });
});

// 404 handler
app.use((req, res) => {
    res.status(404).json({
        error: 'Not Found',
        message: `Route ${req.method} ${req.url} not found`,
        timestamp: new Date().toISOString()
    });
});

// Error handler
app.use(errorHandler);

// ============================================================================
// SERVER START
// ============================================================================

const server = app.listen(PORT, () => {
    logger.info(`🚀 Nexa Core API listening on port ${PORT}`);
    logger.info(`📊 Environment: ${process.env.NODE_ENV}`);
    logger.info(`🔗 Analyzer Service: ${process.env.ANALYZER_URL}`);
    logger.info(`💾 Database: ${process.env.DATABASE_URL ? 'Connected' : 'Not configured'}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
    logger.info('SIGTERM signal received: closing HTTP server');
    server.close(() => {
        logger.info('HTTP server closed');
        process.exit(0);
    });
});

process.on('SIGINT', () => {
    logger.info('SIGINT signal received: closing HTTP server');
    server.close(() => {
        logger.info('HTTP server closed');
        process.exit(0);
    });
});

module.exports = app;
