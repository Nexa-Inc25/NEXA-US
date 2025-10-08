/**
 * Submissions Router - As-Built Submissions (Crew Foreman Domain)
 */

const express = require('express');
const router = express.Router();
const multer = require('multer');
const { Pool } = require('pg');
const logger = require('../utils/logger');
const { requireRole } = require('../middleware/auth');

const pool = new Pool({
    connectionString: process.env.DATABASE_URL
});

// File upload for photos
const upload = multer({
    storage: multer.memoryStorage(),
    limits: {
        fileSize: 10 * 1024 * 1024  // 10MB per photo
    }
});

/**
 * POST /api/submissions
 * Submit as-built from field (Foreman only)
 */
router.post('/', requireRole(['crew_foreman', 'admin']), upload.array('photos', 20), async (req, res) => {
    const {
        job_id,
        as_built_data,
        equipment_installed,
        measurements,
        weather_conditions,
        crew_notes,
        gps_coordinates,
        submitted_offline
    } = req.body;
    
    if (!job_id || !as_built_data) {
        return res.status(400).json({
            error: 'Missing required fields',
            required: ['job_id', 'as_built_data']
        });
    }
    
    const client = await pool.connect();
    
    try {
        // Verify job exists and foreman is assigned
        const jobResult = await client.query(
            'SELECT id, assigned_foreman_id FROM jobs WHERE id = $1',
            [job_id]
        );
        
        if (jobResult.rows.length === 0) {
            return res.status(404).json({ error: 'Job not found' });
        }
        
        // TODO: Upload photos to S3 and get URLs
        // For now, we'll just store empty array
        const photos = [];  // Future: S3 URLs from req.files
        
        const result = await client.query(`
            INSERT INTO submissions (
                job_id,
                foreman_id,
                as_built_data,
                photos,
                equipment_installed,
                measurements,
                weather_conditions,
                crew_notes,
                gps_coordinates,
                submitted_offline,
                submitted_from,
                device_info
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING *
        `, [
            job_id,
            req.user.id,
            typeof as_built_data === 'string' ? as_built_data : JSON.stringify(as_built_data),
            JSON.stringify(photos),
            equipment_installed ? JSON.stringify(equipment_installed) : null,
            measurements ? JSON.stringify(measurements) : null,
            weather_conditions || null,
            crew_notes || null,
            gps_coordinates ? JSON.stringify(gps_coordinates) : null,
            submitted_offline === 'true' || submitted_offline === true,
            req.headers['user-agent']?.includes('Mobile') ? 'mobile' : 'web',
            JSON.stringify({ user_agent: req.headers['user-agent'] })
        ]);
        
        // Update job status
        await client.query(
            'UPDATE jobs SET status = $1 WHERE id = $2',
            ['submitted', job_id]
        );
        
        // Log activity
        await client.query(`
            INSERT INTO activity_log (user_id, action, entity_type, entity_id, details)
            VALUES ($1, $2, $3, $4, $5)
        `, [req.user.id, 'submit_as_built', 'submission', result.rows[0].id, JSON.stringify({ job_id })]);
        
        logger.info(`As-built submitted for job ${job_id} by ${req.user.name}`);
        
        res.status(201).json(result.rows[0]);
    } catch (error) {
        logger.error('Error creating submission:', error);
        res.status(500).json({ error: 'Failed to create submission' });
    } finally {
        client.release();
    }
});

/**
 * GET /api/submissions
 * List submissions (filtered by role)
 */
router.get('/', async (req, res) => {
    const { status, job_id } = req.query;
    
    try {
        let query = `
            SELECT 
                s.*,
                j.job_number,
                j.location,
                j.work_type,
                u.name as foreman_name
            FROM submissions s
            JOIN jobs j ON s.job_id = j.id
            JOIN users u ON s.foreman_id = u.id
            WHERE 1=1
        `;
        const params = [];
        
        // Filter by role
        if (req.user.role === 'crew_foreman') {
            params.push(req.user.id);
            query += ` AND s.foreman_id = $${params.length}`;
        }
        
        if (status) {
            params.push(status);
            query += ` AND s.status = $${params.length}`;
        }
        
        if (job_id) {
            params.push(job_id);
            query += ` AND s.job_id = $${params.length}`;
        }
        
        query += ' ORDER BY s.submitted_at DESC';
        
        const result = await pool.query(query, params);
        
        res.json({
            count: result.rows.length,
            submissions: result.rows
        });
    } catch (error) {
        logger.error('Error fetching submissions:', error);
        res.status(500).json({ error: 'Failed to fetch submissions' });
    }
});

/**
 * GET /api/submissions/:id
 * Get submission details
 */
router.get('/:id', async (req, res) => {
    try {
        const result = await pool.query(`
            SELECT 
                s.*,
                j.job_number,
                j.location,
                j.work_type,
                j.gf_id,
                u.name as foreman_name,
                qa.name as qa_reviewer_name
            FROM submissions s
            JOIN jobs j ON s.job_id = j.id
            JOIN users u ON s.foreman_id = u.id
            LEFT JOIN users qa ON s.qa_reviewed_by = qa.id
            WHERE s.id = $1
        `, [req.params.id]);
        
        if (result.rows.length === 0) {
            return res.status(404).json({ error: 'Submission not found' });
        }
        
        res.json(result.rows[0]);
    } catch (error) {
        logger.error('Error fetching submission:', error);
        res.status(500).json({ error: 'Failed to fetch submission' });
    }
});

/**
 * POST /api/submissions/:id/review
 * QA review submission
 */
router.post('/:id/review', requireRole(['qa', 'admin']), async (req, res) => {
    const { id } = req.params;
    const { status, notes } = req.body;
    
    if (!status || !['approved', 'returned'].includes(status)) {
        return res.status(400).json({
            error: 'Invalid status',
            allowed: ['approved', 'returned']
        });
    }
    
    const client = await pool.connect();
    
    try {
        const result = await client.query(`
            UPDATE submissions
            SET status = $1,
                qa_reviewed_by = $2,
                qa_reviewed_at = CURRENT_TIMESTAMP
            WHERE id = $3
            RETURNING *
        `, [status, req.user.id, id]);
        
        if (result.rows.length === 0) {
            return res.status(404).json({ error: 'Submission not found' });
        }
        
        // Update job status
        const newJobStatus = status === 'approved' ? 'approved' : 'under_qa';
        await client.query(
            'UPDATE jobs SET status = $1 WHERE id = $2',
            [newJobStatus, result.rows[0].job_id]
        );
        
        // Log activity
        await client.query(`
            INSERT INTO activity_log (user_id, action, entity_type, entity_id, details)
            VALUES ($1, $2, $3, $4, $5)
        `, [req.user.id, 'review_submission', 'submission', id, JSON.stringify({ status, notes })]);
        
        logger.info(`Submission ${id} reviewed by ${req.user.name}: ${status}`);
        
        res.json(result.rows[0]);
    } catch (error) {
        logger.error('Error reviewing submission:', error);
        res.status(500).json({ error: 'Failed to review submission' });
    } finally {
        client.release();
    }
});

module.exports = router;
