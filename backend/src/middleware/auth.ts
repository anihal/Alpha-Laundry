import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { AppError } from './errorHandler';
import pool from '../config/database';
import { config } from '../config/env';

interface JwtPayload {
  id: string;
  role: 'student' | 'admin';
}

declare global {
  namespace Express {
    interface Request {
      user?: {
        id: string;
        role: 'student' | 'admin';
      };
    }
  }
}

export const protect = async (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  try {
    // Get token from header
    const authHeader = req.headers.authorization;
    if (!authHeader?.startsWith('Bearer ')) {
      throw new AppError('Not authorized to access this route', 401);
    }

    const token = authHeader.split(' ')[1];

    // Verify token
    const decoded = jwt.verify(
      token,
      config.jwt.secret
    ) as JwtPayload;

    // Check if user exists
    let user;
    if (decoded.role === 'student') {
      const result = await pool.query(
        'SELECT student_id as id, name FROM students WHERE student_id = $1',
        [decoded.id]
      );
      user = result.rows[0];
    } else {
      const result = await pool.query(
        'SELECT id, username FROM admins WHERE id = $1',
        [decoded.id]
      );
      user = result.rows[0];
    }

    if (!user) {
      throw new AppError('User not found', 404);
    }

    // Add user to request
    req.user = {
      id: user.id,
      role: decoded.role
    };

    next();
  } catch (error) {
    next(new AppError('Not authorized to access this route', 401));
  }
};

export const restrictTo = (...roles: ('student' | 'admin')[]) => {
  return (req: Request, res: Response, next: NextFunction) => {
    if (!req.user) {
      return next(new AppError('Not authorized to access this route', 401));
    }

    if (!roles.includes(req.user.role)) {
      return next(new AppError('Not authorized to access this route', 403));
    }

    next();
  };
}; 