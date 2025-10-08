/**
 * Audits Router - Go-Back Contest ing with Analyzer Integration
 * 
 * Workflow:
 * 1. QA receives PGE go-back PDF
 * 2. QA uploads to /contest-audit
 * 3. API calls Multi-Spec Analyzer service
 * 4. Analyzer returns repeal analysis with spec citations
 * 5. API saves results to DB
 * 6. QA reviews and files contest if confidence > threshold
 */

const express = require('express');
const router = express.Router();
const multer = require('multer');
const FormData = require('form-data');
const fetch = require('node-fetch');
const { Pool } = require('pg');
const logger = require('../utils/logger');
const { requireRole } = require('../middleware/auth');

// Database pool
const pool = new Pool({
    connectionString: process.env.DATABASE_URL
});

// File upload configuration
const upload = multer({
    storage: multer.memoryStorage(),
    limits: {
        fileSize: (parseInt(process.env.MAX_UPLOAD_SIZE_MB) || 100) * 1024 * 1024
    },
    fileFilter: (req, file, cb) => {
        if (file.mimetype === 'application/pdf') {
            cb(null, true);
        } else {
            cb(new Error('Only PDF files are allowed'));
        }
    }
});

/**
 * POST /api/audits/contest
 * Contest a PGE go-back using the Multi-Spec Analyzer
 * 
 * Requires: QA or Admin role
 * Body: {
 *   submission_id: number,
 *   pge_reference_number: string,
 *   pge_inspector: string (optional)
 * }
 * File: PGE audit/go-back PDF
 */
router.post('/contest', requireRole(['qa', 'admin']), upload.single('audit_pdf'), async (req, res) => {
    const { submission_id, pge_reference_number, pge_inspector } = req.body;
    const auditFile = req.file;
    
    if (!submission_id || !pge_reference_number || !auditFile) {
        return res.status(400).json({
            error: 'Missing required fields',
            required: ['submission_id', 'pge_reference_number', 'audit_pdf']
        });
    }
    
    const client = await pool.connect();
    
    try {
        logger.info(`Contest audit for submission ${submission_id}`);
        
        // 1. Verify submission exists
        const submissionResult = await client.query(
            'SELECT id, job_id, foreman_id FROM submissions WHERE id = $1',
            [submission_id]
        );
        
        if (submissionResult.rows.length === 0) {
            return res.status(404).json({ error: 'Submission not found' });
        }
        
        // 2. Call Multi-Spec Analyzer Service
        logger.info('Calling Multi-Spec Analyzer...');
        
        const formData = new FormData();
        formData.append('file', auditFile.buffer, {
            filename: auditFile.originalname,
            contentType: 'application/pdf'
        });
        
        const analyzerResponse = await fetch(
            `${process.env.ANALYZER_URL}/analyze-audit`,
            {
                method: 'POST',
                body: formData,
                headers: formData.getHeaders(),
                timeout: parseInt(process.env.ANALYZER_TIMEOUT) || 60000
            }
        );
        
        if (!analyzerResponse.ok) {
            throw new Error(`Analyzer service returned ${analyzerResponse.status}: ${await analyzerResponse.text()}`);
        }
        
        const repealAnalysis = await analyzerResponse.json();
        
        logger.info(`Analyzer returned ${repealAnalysis.length} infractions`);
        
        // 3. Check if any infractions are contestable
        const contestable = repealAnalysis.some(
            infraction => infraction.status === 'REPEALABLE' && infraction.confidence > 70
        );
        
        // 4. Upload PDF to S3 (optional - for now we'll skip and store in DB)
        // TODO: Implement S3 upload for PDF storage
        const pge_audit_pdf_url = null;  // Future: S3 URL
        
        // 5. Save audit record to database
        const auditResult = await client.query(`
            INSERT INTO audits (
                submission_id,
                pge_audit_pdf_url,
                pge_audit_date,
                pge_inspector,
                pge_reference_number,
                repeal_analysis,
                contestable
            ) VALUES ($1, $2, CURRENT_DATE, $3, $4, $5, $6)
            RETURNING *
        `, [
            submission_id,
            pge_audit_pdf_url,
            pge_inspector || null,
            pge_reference_number,
            JSON.stringify(repealAnalysis),
            contestable
        ]);
        
        const audit = auditResult.rows[0];
        
        // 6. Update submission status to 'go_back'
        await client.query(
            'UPDATE submissions SET status = $1 WHERE id = $2',
            ['go_back', submission_id]
        );
        
        // 7. Log activity
        await client.query(`
            INSERT INTO activity_log (user_id, action, entity_type, entity_id, details)
            VALUES ($1, $2, $3, $4, $5)
        `, [
            req.user.id,
            'contest_audit',
            'audit',
            audit.id,
            JSON.stringify({ pge_reference_number, contestable })
        ]);
        
        logger.info(`Audit ${audit.id} created, contestable: ${contestable}`);
        
        // 8. Return results
        res.json({
            success: true,
            audit: {
                id: audit.id,
                uuid: audit.uuid,
                submission_id: audit.submission_id,
                pge_reference_number: audit.pge_reference_number,
                contestable: audit.contestable,
                created_at: audit.created_at
            },
            analysis: repealAnalysis,
            summary: {
                total_infractions: repealAnalysis.length,
                repealable_count: repealAnalysis.filter(i => i.status === 'REPEALABLE').length,
                high_confidence_count: repealAnalysis.filter(i => i.confidence > 80).length,
                recommendation: contestable ? 'CONTEST_RECOMMENDED' : 'NO_CONTEST'
            }
        });
        
    } catch (error) {
        logger.error('Error contesting audit:', error);
        res.status(500).json({
            error: 'Failed to analyze audit',
            message: error.message,
            details: process.env.NODE_ENV === 'development' ? error.stack : undefined
        });
    } finally {
        client.release();
    }
});

/**
 * GET /api/audits/contestable
 * Get all contestable audits that haven't been filed yet
 * 
 * Requires: QA or Admin role
 */
router.get('/contestable', requireRole(['qa', 'admin']), async (req, res) => {
    try {
        const result = await pool.query(`
            SELECT 
                a.*,
                s.uuid as submission_uuid,
                j.job_number,
                j.location,
                u.name as foreman_name
            FROM audits a
            JOIN submissions s ON a.submission_id = s.id
            JOIN jobs j ON s.job_id = j.id
            JOIN users u ON s.foreman_id = u.id
            WHERE a.contestable = true 
            AND a.contest_filed = false
            ORDER BY a.created_at DESC
        `);
        
        res.json({
            count: result.rows.length,
            audits: result.rows
        });
    } catch (error) {
        logger.error('Error fetching contestable audits:', error);
        res.status(500).json({ error: 'Failed to fetch audits' });
    }
});

/**
 * POST /api/audits/:id/file-contest
 * Mark an audit as contest filed
 * 
 * Requires: QA or Admin role
 */
router.post('/:id/file-contest', requireRole(['qa', 'admin']), async (req, res) => {
    const { id } = req.params;
    const { contest_notes } = req.body;
    
    const client = await pool.connect();
    
    try {
        const result = await client.query(`
            UPDATE audits
            SET contest_filed = true,
                contest_filed_date = CURRENT_DATE,
                contest_notes = $1
            WHERE id = $2
            RETURNING *
        `, [contest_notes || null, id]);
        
        if (result.rows.length === 0) {
            return res.status(404).json({ error: 'Audit not found' });
        }
        
        // Log activity
        await client.query(`
            INSERT INTO activity_log (user_id, action, entity_type, entity_id, details)
            VALUES ($1, $2, $3, $4, $5)
        `, [
            req.user.id,
            'file_contest',
            'audit',
            id,
            JSON.stringify({ contest_notes })
        ]);
        
        logger.info(`Contest filed for audit ${id}`);
        
        res.json({
            success: true,
            audit: result.rows[0]
        });
    } catch (error) {
        logger.error('Error filing contest:', error);
        res.status(500).json({ error: 'Failed to file contest' });
    } finally {
        client.release();
    }
});

/**
 * GET /api/audits/:id
 * Get audit details by ID
 */
router.get('/:id', async (req, res) => {
    try {
        const result = await pool.query(`
            SELECT 
                a.*,
                s.uuid as submission_uuid,
                s.as_built_data,
                j.job_number,
                j.location,
                j.work_type,
                u.name as foreman_name
            FROM audits a
            JOIN submissions s ON a.submission_id = s.id
            JOIN jobs j ON s.job_id = j.id
            JOIN users u ON s.foreman_id = u.id
            WHERE a.id = $1
        `, [req.params.id]);
        
        if (result.rows.length === 0) {
            return res.status(404).json({ error: 'Audit not found' });
        }
        
        res.json(result.rows[0]);
    } catch (error) {
        logger.error('Error fetching audit:', error);
        res.status(500).json({ error: 'Failed to fetch audit' });
    }
});

module.exports = router;
