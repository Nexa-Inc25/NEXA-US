const express = require('express');
const router = express.Router();

const authRoutes = require('./auth');
const todayRoutes = require('./today');
const syncRoutes = require('./sync');
const presignRoutes = require('./presign');
const photoQaRoutes = require('./photoQa');
const timesheetRoutes = require('./timesheet');
const closeoutRoutes = require('./closeout');
const notifyRoutes = require('./notify');

router.use(authRoutes);
router.use(todayRoutes);
router.use(syncRoutes);
router.use(presignRoutes);
router.use(photoQaRoutes);
router.use(timesheetRoutes);
router.use(closeoutRoutes);
router.use(notifyRoutes);

module.exports = router;
