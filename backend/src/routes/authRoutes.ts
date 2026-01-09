import express from 'express';
import { body } from 'express-validator';
import { login, registerAdmin, verify } from '../controllers/authController';
import { validateRequest } from '../middleware/validateRequest';
import { protect, restrictTo } from '../middleware/auth';

const router = express.Router();

router.post(
  '/login',
  [
    body('username').notEmpty().withMessage('Username is required'),
    body('password').notEmpty().withMessage('Password is required'),
    validateRequest
  ],
  login
);

router.get('/verify', protect, verify);

router.post(
  '/register',
  [
    protect,
    restrictTo('admin'),
    body('username').notEmpty().withMessage('Username is required'),
    body('password')
      .isLength({ min: 6 })
      .withMessage('Password must be at least 6 characters long'),
    validateRequest
  ],
  registerAdmin
);

export default router; 