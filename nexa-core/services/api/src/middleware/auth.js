/**
 * Authentication Middleware
 */

const jwt = require('jsonwebtoken');
const { Pool } = require('pg');
const logger = require('../utils/logger');

const pool = new Pool({
    connectionString: process.env.DATABASE_URL
});

/**
 * Middleware to authenticate requests via JWT or API Key
 */
const authMiddleware = async (req, res, next) => {
    try {
        // Check for API Key first (for mobile/foreman access)
        const apiKey = req.header('X-API-Key');
        
        if (apiKey) {
            const result = await pool.query(
                'SELECT id, email, name, role FROM users WHERE api_key = $1 AND active = true',
                [apiKey]
            );
            
            if (result.rows.length > 0) {
                req.user = result.rows[0];
                return next();
            }
            
            return res.status(401).json({ error: 'Invalid API key' });
        }
        
        // Check for JWT token (for web dashboard)
        const authHeader = req.header('Authorization');
        
        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            return res.status(401).json({ error: 'No authentication token provided' });
        }
        
        const token = authHeader.substring(7);
        
        try {
            const decoded = jwt.verify(token, process.env.JWT_SECRET);
            
            const result = await pool.query(
                'SELECT id, email, name, role FROM users WHERE id = $1 AND active = true',
                [decoded.userId]
            );
            
            if (result.rows.length === 0) {
                return res.status(401).json({ error: 'User not found or inactive' });
            }
            
            req.user = result.rows[0];
            next();
        } catch (error) {
            if (error.name === 'TokenExpiredError') {
                return res.status(401).json({ error: 'Token expired' });
            }
            return res.status(401).json({ error: 'Invalid token' });
        }
        
    } catch (error) {
        logger.error('Authentication error:', error);
        res.status(500).json({ error: 'Authentication failed' });
    }
};

/**
 * Middleware to require specific role(s)
 * Usage: requireRole(['qa', 'admin'])
 */
const requireRole = (roles) => {
    return (req, res, next) => {
        if (!req.user) {
            return res.status(401).json({ error: 'Not authenticated' });
        }
        
        if (!roles.includes(req.user.role)) {
            return res.status(403).json({
                error: 'Insufficient permissions',
                required_roles: roles,
                your_role: req.user.role
            });
        }
        
        next();
    };
};

module.exports = {
    authMiddleware,
    requireRole
};
