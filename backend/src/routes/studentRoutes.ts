import express from 'express';
import { body } from 'express-validator';
import { protect, restrictTo } from '../middleware/auth';
import { validateRequest } from '../middleware/validateRequest';
import {
  getDashboard,
  submitRequest,
  getHistory
} from '../controllers/studentController';

const router = express.Router();

// Protect all routes
router.use(protect);
router.use(restrictTo('student'));

// Get student dashboard
router.get('/dashboard', getDashboard);

// Submit new laundry request
router.post(
  '/submit',
  [
    body('num_clothes')
      .isInt({ min: 1 })
      .withMessage('Number of clothes must be at least 1'),
    validateRequest
  ],
  submitRequest
);

// Get laundry history
router.get('/history', getHistory);

export default router; 