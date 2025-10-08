/**
 * Jobs Router - Job Management (General Foreman Domain)
 */

const express = require('express');
const router = express.Router();
const { Pool } = require('pg');
const { v4: uuidv4 } = require('uuid');
const logger = require('../utils/logger');
const { requireRole } = require('../middleware/auth');

const pool = new Pool({
    connectionString: process.env.DATABASE_URL
});

/**
 * POST /api/jobs
 * Create a new job (General Foreman only)
 */
router.post('/', requireRole(['general_foreman', 'admin']), async (req, res) => {
    const {
        job_number,
        location,
        work_type,
        scheduled_date,
        assigned_foreman_id,
        pre_field_notes,
        required_specs,
        materials
    } = req.body;
    
    if (!job_number || !location || !work_type || !scheduled_date) {
        return res.status(400).json({
            error: 'Missing required fields',
            required: ['job_number', 'location', 'work_type', 'scheduled_date']
        });
    }
    
    const client = await pool.connect();
    
    try {
        // Generate QR code data (encrypted job ID + auth token)
        const qr_code_data = Buffer.from(JSON.stringify({
            job_id: job_number,
            token: uuidv4(),
            created_at: new Date().toISOString()
        })).toString('base64');
        
        const result = await client.query(`
            INSERT INTO jobs (
                job_number,
                gf_id,
                assigned_foreman_id,
                location,
                work_type,
                scheduled_date,
                pre_field_notes,
                required_specs,
                materials,
                qr_code_data,
                status
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING *
        `, [
            job_number,
            req.user.id,
            assigned_foreman_id || null,
            JSON.stringify(location),
            work_type,
            scheduled_date,
            pre_field_notes || null,
            required_specs ? JSON.stringify(required_specs) : null,
            materials ? JSON.stringify(materials) : null,
            qr_code_data,
            assigned_foreman_id ? 'assigned' : 'planned'
        ]);
        
        // Log activity
        await client.query(`
            INSERT INTO activity_log (user_id, action, entity_type, entity_id, details)
            VALUES ($1, $2, $3, $4, $5)
        `, [req.user.id, 'create_job', 'job', result.rows[0].id, JSON.stringify({ job_number })]);
        
        logger.info(`Job ${job_number} created by ${req.user.name}`);
        
        res.status(201).json(result.rows[0]);
    } catch (error) {
        logger.error('Error creating job:', error);
        
        if (error.code === '23505') {  // Unique violation
            return res.status(400).json({ error: 'Job number already exists' });
        }
        
        res.status(500).json({ error: 'Failed to create job' });
    } finally {
        client.release();
    }
});

/**
 * GET /api/jobs
 * List jobs (filtered by role)
 */
router.get('/', async (req, res) => {
    const { status, foreman_id, scheduled_after, scheduled_before } = req.query;
    
    try {
        let query = `
            SELECT 
                j.*,
                u.name as gf_name,
                f.name as foreman_name
            FROM jobs j
            JOIN users u ON j.gf_id = u.id
            LEFT JOIN users f ON j.assigned_foreman_id = f.id
            WHERE 1=1
        `;
        const params = [];
        
        // Filter by role
        if (req.user.role === 'general_foreman') {
            params.push(req.user.id);
            query += ` AND j.gf_id = $${params.length}`;
        } else if (req.user.role === 'crew_foreman') {
            params.push(req.user.id);
            query += ` AND j.assigned_foreman_id = $${params.length}`;
        }
        
        // Additional filters
        if (status) {
            params.push(status);
            query += ` AND j.status = $${params.length}`;
        }
        
        if (foreman_id) {
            params.push(foreman_id);
            query += ` AND j.assigned_foreman_id = $${params.length}`;
        }
        
        if (scheduled_after) {
            params.push(scheduled_after);
            query += ` AND j.scheduled_date >= $${params.length}`;
        }
        
        if (scheduled_before) {
            params.push(scheduled_before);
            query += ` AND j.scheduled_date <= $${params.length}`;
        }
        
        query += ' ORDER BY j.scheduled_date DESC';
        
        const result = await pool.query(query, params);
        
        res.json({
            count: result.rows.length,
            jobs: result.rows
        });
    } catch (error) {
        logger.error('Error fetching jobs:', error);
        res.status(500).json({ error: 'Failed to fetch jobs' });
    }
});

/**
 * GET /api/jobs/:id
 * Get job details
 */
router.get('/:id', async (req, res) => {
    try {
        const result = await pool.query(`
            SELECT 
                j.*,
                u.name as gf_name,
                f.name as foreman_name,
                (SELECT COUNT(*) FROM submissions WHERE job_id = j.id) as submission_count
            FROM jobs j
            JOIN users u ON j.gf_id = u.id
            LEFT JOIN users f ON j.assigned_foreman_id = f.id
            WHERE j.id = $1
        `, [req.params.id]);
        
        if (result.rows.length === 0) {
            return res.status(404).json({ error: 'Job not found' });
        }
        
        res.json(result.rows[0]);
    } catch (error) {
        logger.error('Error fetching job:', error);
        res.status(500).json({ error: 'Failed to fetch job' });
    }
});

/**
 * PUT /api/jobs/:id
 * Update job (GF only)
 */
router.put('/:id', requireRole(['general_foreman', 'admin']), async (req, res) => {
    const { id } = req.params;
    const updates = req.body;
    
    const client = await pool.connect();
    
    try {
        // Verify ownership
        const checkResult = await client.query(
            'SELECT gf_id FROM jobs WHERE id = $1',
            [id]
        );
        
        if (checkResult.rows.length === 0) {
            return res.status(404).json({ error: 'Job not found' });
        }
        
        if (req.user.role === 'general_foreman' && checkResult.rows[0].gf_id !== req.user.id) {
            return res.status(403).json({ error: 'Not authorized to update this job' });
        }
        
        // Build update query dynamically
        const allowedFields = [
            'assigned_foreman_id', 'location', 'work_type', 'scheduled_date',
            'pre_field_notes', 'required_specs', 'materials', 'status'
        ];
        
        const setClause = [];
        const values = [];
        let paramCount = 1;
        
        for (const field of allowedFields) {
            if (updates[field] !== undefined) {
                setClause.push(`${field} = $${paramCount}`);
                values.push(
                    ['location', 'required_specs', 'materials'].includes(field) && typeof updates[field] === 'object'
                        ? JSON.stringify(updates[field])
                        : updates[field]
                );
                paramCount++;
            }
        }
        
        if (setClause.length === 0) {
            return res.status(400).json({ error: 'No valid fields to update' });
        }
        
        values.push(id);
        
        const result = await client.query(
            `UPDATE jobs SET ${setClause.join(', ')} WHERE id = $${paramCount} RETURNING *`,
            values
        );
        
        // Log activity
        await client.query(`
            INSERT INTO activity_log (user_id, action, entity_type, entity_id, details)
            VALUES ($1, $2, $3, $4, $5)
        `, [req.user.id, 'update_job', 'job', id, JSON.stringify(updates)]);
        
        logger.info(`Job ${id} updated by ${req.user.name}`);
        
        res.json(result.rows[0]);
    } catch (error) {
        logger.error('Error updating job:', error);
        res.status(500).json({ error: 'Failed to update job' });
    } finally {
        client.release();
    }
});

/**
 * GET /api/jobs/:id/qr
 * Get QR code data for mobile access
 */
router.get('/:id/qr', async (req, res) => {
    try {
        const result = await pool.query(
            'SELECT id, job_number, qr_code_data, status FROM jobs WHERE id = $1',
            [req.params.id]
        );
        
        if (result.rows.length === 0) {
            return res.status(404).json({ error: 'Job not found' });
        }
        
        const job = result.rows[0];
        
        res.json({
            job_id: job.id,
            job_number: job.job_number,
            qr_code_data: job.qr_code_data,
            qr_url: `nexa://job/${job.qr_code_data}`  // Deep link for mobile app
        });
    } catch (error) {
        logger.error('Error fetching QR code:', error);
        res.status(500).json({ error: 'Failed to fetch QR code' });
    }
});

module.exports = router;
