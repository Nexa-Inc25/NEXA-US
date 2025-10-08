/**
 * Health Check Router
 */

const express = require('express');
const router = express.Router();
const { Pool } = require('pg');
const fetch = require('node-fetch');
const logger = require('../utils/logger');

const pool = new Pool({
    connectionString: process.env.DATABASE_URL
});

/**
 * GET /health
 * System health check
 */
router.get('/', async (req, res) => {
    const health = {
        status: 'ok',
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
        checks: {
            api: 'ok',
            database: 'unknown',
            analyzer: 'unknown'
        }
    };
    
    // Check database
    try {
        await pool.query('SELECT 1');
        health.checks.database = 'ok';
    } catch (error) {
        logger.error('Database health check failed:', error);
        health.checks.database = 'error';
        health.status = 'degraded';
    }
    
    // Check analyzer service
    try {
        const analyzerHealth = await fetch(`${process.env.ANALYZER_URL}/health`, {
            timeout: 5000
        });
        
        if (analyzerHealth.ok) {
            const data = await analyzerHealth.json();
            health.checks.analyzer = {
                status: 'ok',
                spec_learned: data.spec_learned || false
            };
        } else {
            health.checks.analyzer = 'error';
            health.status = 'degraded';
        }
    } catch (error) {
        logger.error('Analyzer health check failed:', error);
        health.checks.analyzer = 'error';
        health.status = 'degraded';
    }
    
    const statusCode = health.status === 'ok' ? 200 : 503;
    res.status(statusCode).json(health);
});

module.exports = router;
