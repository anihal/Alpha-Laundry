import express from 'express';
import { body } from 'express-validator';
import { protect, restrictTo } from '../middleware/auth';
import { validateRequest } from '../middleware/validateRequest';
import {
  getDashboard,
  updateRequestStatus,
  getAnalytics
} from '../controllers/adminController';

const router = express.Router();

// Protect all routes
router.use(protect);
router.use(restrictTo('admin'));

// Get admin dashboard
router.get('/dashboard', getDashboard);

// Update request status
router.patch(
  '/update-status',
  [
    body('request_id').isInt().withMessage('Request ID must be a number'),
    body('status')
      .isIn(['processing', 'completed'])
      .withMessage('Status must be either processing or completed'),
    validateRequest
  ],
  updateRequestStatus
);

// Get analytics
router.get('/analytics', getAnalytics);

export default router; 