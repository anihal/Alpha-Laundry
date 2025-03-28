import { Request, Response, NextFunction } from 'express';
import bcrypt from 'bcrypt';
import jwt, { SignOptions } from 'jsonwebtoken';
import { AppError } from '../middleware/errorHandler';
import pool from '../config/database';

export const login = async (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  try {
    const { username, password } = req.body;

    // Check if user is student or admin
    let user;
    let role: 'student' | 'admin';

    // Try to find student
    const studentResult = await pool.query(
      'SELECT student_id, name FROM students WHERE student_id = $1',
      [username]
    );

    if (studentResult.rows.length > 0) {
      user = studentResult.rows[0];
      role = 'student';
    } else {
      // Try to find admin
      const adminResult = await pool.query(
        'SELECT id, username, password_hash FROM admins WHERE username = $1',
        [username]
      );

      if (adminResult.rows.length === 0) {
        throw new AppError('Invalid credentials', 401);
      }

      const isValidPassword = await bcrypt.compare(
        password,
        adminResult.rows[0].password_hash
      );

      if (!isValidPassword) {
        throw new AppError('Invalid credentials', 401);
      }

      user = adminResult.rows[0];
      role = 'admin';
    }

    // Generate JWT token
    const token = jwt.sign(
      {
        id: role === 'student' ? user.student_id : user.id,
        role
      },
      process.env.JWT_SECRET || 'your-secret-key',
      {
        expiresIn: process.env.JWT_EXPIRES_IN || '24h'
      } as SignOptions
    );

    res.json({
      status: 'success',
      token,
      user: {
        id: role === 'student' ? user.student_id : user.id,
        name: role === 'student' ? user.name : user.username,
        role
      }
    });
  } catch (error) {
    next(error);
  }
};

export const registerAdmin = async (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  try {
    const { username, password } = req.body;

    // Check if username already exists
    const existingAdmin = await pool.query(
      'SELECT id FROM admins WHERE username = $1',
      [username]
    );

    if (existingAdmin.rows.length > 0) {
      throw new AppError('Username already exists', 400);
    }

    // Hash password
    const salt = await bcrypt.genSalt(10);
    const passwordHash = await bcrypt.hash(password, salt);

    // Create new admin
    const result = await pool.query(
      'INSERT INTO admins (username, password_hash) VALUES ($1, $2) RETURNING id, username',
      [username, passwordHash]
    );

    res.status(201).json({
      status: 'success',
      data: {
        admin: result.rows[0]
      }
    });
  } catch (error) {
    next(error);
  }
}; 