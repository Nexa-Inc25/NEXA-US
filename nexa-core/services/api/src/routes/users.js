/**
 * Users Router - User Management & Authentication
 */

const express = require('express');
const router = express.Router();
const jwt = require('jsonwebtoken');
const bcrypt = require('bcrypt');
const { Pool } = require('pg');
const logger = require('../utils/logger');
const { requireRole } = require('../middleware/auth');

const pool = new Pool({
    connectionString: process.env.DATABASE_URL
});

/**
 * POST /api/users/login
 * Authenticate user and return JWT
 */
router.post('/login', async (req, res) => {
    const { email, password } = req.body;
    
    if (!email || !password) {
        return res.status(400).json({
            error: 'Missing credentials',
            required: ['email', 'password']
        });
    }
    
    try {
        const result = await pool.query(
            'SELECT id, email, name, role, active FROM users WHERE email = $1',
            [email.toLowerCase()]
        );
        
        if (result.rows.length === 0) {
            return res.status(401).json({ error: 'Invalid credentials' });
        }
        
        const user = result.rows[0];
        
        if (!user.active) {
            return res.status(403).json({ error: 'Account is inactive' });
        }
        
        // TODO: Add password hashing in production
        // For now, using API keys for authentication
        
        // Generate JWT token
        const token = jwt.sign(
            { userId: user.id, role: user.role },
            process.env.JWT_SECRET,
            { expiresIn: process.env.JWT_EXPIRES_IN || '7d' }
        );
        
        // Log login
        await pool.query(`
            INSERT INTO activity_log (user_id, action, details)
            VALUES ($1, $2, $3)
        `, [user.id, 'login', JSON.stringify({ method: 'jwt' })]);
        
        logger.info(`User ${user.email} logged in`);
        
        res.json({
            token,
            user: {
                id: user.id,
                email: user.email,
                name: user.name,
                role: user.role
            }
        });
    } catch (error) {
        logger.error('Login error:', error);
        res.status(500).json({ error: 'Login failed' });
    }
});

/**
 * GET /api/users/me
 * Get current user info
 */
router.get('/me', async (req, res) => {
    try {
        const result = await pool.query(
            'SELECT id, email, name, role, phone, created_at FROM users WHERE id = $1',
            [req.user.id]
        );
        
        if (result.rows.length === 0) {
            return res.status(404).json({ error: 'User not found' });
        }
        
        res.json(result.rows[0]);
    } catch (error) {
        logger.error('Error fetching user:', error);
        res.status(500).json({ error: 'Failed to fetch user' });
    }
});

/**
 * GET /api/users
 * List users (Admin only)
 */
router.get('/', requireRole(['admin']), async (req, res) => {
    const { role, active } = req.query;
    
    try {
        let query = 'SELECT id, email, name, role, phone, active, created_at FROM users WHERE 1=1';
        const params = [];
        
        if (role) {
            params.push(role);
            query += ` AND role = $${params.length}`;
        }
        
        if (active !== undefined) {
            params.push(active === 'true');
            query += ` AND active = $${params.length}`;
        }
        
        query += ' ORDER BY created_at DESC';
        
        const result = await pool.query(query, params);
        
        res.json({
            count: result.rows.length,
            users: result.rows
        });
    } catch (error) {
        logger.error('Error fetching users:', error);
        res.status(500).json({ error: 'Failed to fetch users' });
    }
});

/**
 * POST /api/users
 * Create new user (Admin only)
 */
router.post('/', requireRole(['admin']), async (req, res) => {
    const { email, name, role, phone } = req.body;
    
    if (!email || !name || !role) {
        return res.status(400).json({
            error: 'Missing required fields',
            required: ['email', 'name', 'role']
        });
    }
    
    if (!['general_foreman', 'crew_foreman', 'qa', 'admin'].includes(role)) {
        return res.status(400).json({
            error: 'Invalid role',
            allowed: ['general_foreman', 'crew_foreman', 'qa', 'admin']
        });
    }
    
    const client = await pool.connect();
    
    try {
        // Generate API key
        const api_key = `${role.substring(0, 3)}_${Date.now()}_${Math.random().toString(36).substring(7)}`;
        
        const result = await client.query(`
            INSERT INTO users (email, name, role, phone, api_key)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, email, name, role, phone, api_key, created_at
        `, [email.toLowerCase(), name, role, phone || null, api_key]);
        
        logger.info(`User created: ${email} (${role})`);
        
        res.status(201).json(result.rows[0]);
    } catch (error) {
        logger.error('Error creating user:', error);
        
        if (error.code === '23505') {
            return res.status(400).json({ error: 'Email already exists' });
        }
        
        res.status(500).json({ error: 'Failed to create user' });
    } finally {
        client.release();
    }
});

/**
 * PUT /api/users/:id
 * Update user (Admin only)
 */
router.put('/:id', requireRole(['admin']), async (req, res) => {
    const { id } = req.params;
    const { name, phone, role, active } = req.body;
    
    const client = await pool.connect();
    
    try {
        const setClause = [];
        const values = [];
        let paramCount = 1;
        
        if (name !== undefined) {
            setClause.push(`name = $${paramCount}`);
            values.push(name);
            paramCount++;
        }
        
        if (phone !== undefined) {
            setClause.push(`phone = $${paramCount}`);
            values.push(phone);
            paramCount++;
        }
        
        if (role !== undefined) {
            setClause.push(`role = $${paramCount}`);
            values.push(role);
            paramCount++;
        }
        
        if (active !== undefined) {
            setClause.push(`active = $${paramCount}`);
            values.push(active);
            paramCount++;
        }
        
        if (setClause.length === 0) {
            return res.status(400).json({ error: 'No fields to update' });
        }
        
        values.push(id);
        
        const result = await client.query(
            `UPDATE users SET ${setClause.join(', ')} WHERE id = $${paramCount} RETURNING id, email, name, role, phone, active, updated_at`,
            values
        );
        
        if (result.rows.length === 0) {
            return res.status(404).json({ error: 'User not found' });
        }
        
        logger.info(`User ${id} updated by ${req.user.name}`);
        
        res.json(result.rows[0]);
    } catch (error) {
        logger.error('Error updating user:', error);
        res.status(500).json({ error: 'Failed to update user' });
    } finally {
        client.release();
    }
});

module.exports = router;
