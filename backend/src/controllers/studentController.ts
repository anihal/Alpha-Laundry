import { Request, Response, NextFunction } from 'express';
import { AppError } from '../middleware/errorHandler';
import pool from '../config/database';

export const getDashboard = async (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  try {
    const studentId = req.user?.id;

    // Get student info and remaining quota
    const studentResult = await pool.query(
      'SELECT student_id, name, remaining_quota FROM students WHERE student_id = $1',
      [studentId]
    );

    if (studentResult.rows.length === 0) {
      throw new AppError('Student not found', 404);
    }

    // Get recent requests
    const requestsResult = await pool.query(
      `SELECT id, num_clothes, status, submission_date 
       FROM laundry_requests 
       WHERE student_id = $1 
       ORDER BY submission_date DESC 
       LIMIT 5`,
      [studentId]
    );

    res.json({
      status: 'success',
      data: {
        student: studentResult.rows[0],
        recent_requests: requestsResult.rows
      }
    });
  } catch (error) {
    next(error);
  }
};

export const submitRequest = async (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  try {
    const studentId = req.user?.id;
    const { num_clothes } = req.body;

    // Check remaining quota
    const studentResult = await pool.query(
      'SELECT remaining_quota FROM students WHERE student_id = $1',
      [studentId]
    );

    if (studentResult.rows.length === 0) {
      throw new AppError('Student not found', 404);
    }

    const remainingQuota = studentResult.rows[0].remaining_quota;
    if (remainingQuota < num_clothes) {
      throw new AppError('Insufficient quota', 400);
    }

    // Start transaction
    const client = await pool.connect();
    try {
      await client.query('BEGIN');

      // Create laundry request
      const requestResult = await client.query(
        `INSERT INTO laundry_requests (student_id, num_clothes) 
         VALUES ($1, $2) 
         RETURNING *`,
        [studentId, num_clothes]
      );

      // Update remaining quota
      await client.query(
        'UPDATE students SET remaining_quota = remaining_quota - $1 WHERE student_id = $2',
        [num_clothes, studentId]
      );

      await client.query('COMMIT');

      res.status(201).json({
        status: 'success',
        data: {
          request: requestResult.rows[0]
        }
      });
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  } catch (error) {
    next(error);
  }
};

export const getHistory = async (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  try {
    const studentId = req.user?.id;

    const result = await pool.query(
      `SELECT id, num_clothes, status, submission_date 
       FROM laundry_requests 
       WHERE student_id = $1 
       ORDER BY submission_date DESC`,
      [studentId]
    );

    res.json({
      status: 'success',
      data: {
        requests: result.rows
      }
    });
  } catch (error) {
    next(error);
  }
}; 