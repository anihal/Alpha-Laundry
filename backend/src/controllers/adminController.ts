import { Request, Response, NextFunction } from 'express';
import { AppError } from '../middleware/errorHandler';
import pool from '../config/database';

export const getDashboard = async (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  try {
    // Get pending requests
    const pendingRequests = await pool.query(
      `SELECT lr.*, s.name as student_name 
       FROM laundry_requests lr 
       JOIN students s ON lr.student_id = s.student_id 
       WHERE lr.status = 'submitted' 
       ORDER BY lr.submission_date ASC`
    );

    // Get total requests count
    const totalRequests = await pool.query(
      'SELECT COUNT(*) as count FROM laundry_requests'
    );

    // Get completed requests count
    const completedRequests = await pool.query(
      "SELECT COUNT(*) as count FROM laundry_requests WHERE status = 'completed'"
    );

    res.json({
      status: 'success',
      data: {
        pending_requests: pendingRequests.rows,
        total_requests: parseInt(totalRequests.rows[0].count),
        completed_requests: parseInt(completedRequests.rows[0].count)
      }
    });
  } catch (error) {
    next(error);
  }
};

export const updateRequestStatus = async (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  try {
    const { request_id, status } = req.body;

    const result = await pool.query(
      `UPDATE laundry_requests 
       SET status = $1 
       WHERE id = $2 
       RETURNING *`,
      [status, request_id]
    );

    if (result.rows.length === 0) {
      throw new AppError('Request not found', 404);
    }

    res.json({
      status: 'success',
      data: {
        request: result.rows[0]
      }
    });
  } catch (error) {
    next(error);
  }
};

export const getAnalytics = async (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  try {
    // Get total clothes processed
    const totalClothes = await pool.query(
      `SELECT SUM(num_clothes) as total 
       FROM laundry_requests 
       WHERE status = 'completed'`
    );

    // Get requests by status
    const requestsByStatus = await pool.query(
      `SELECT status, COUNT(*) as count 
       FROM laundry_requests 
       GROUP BY status`
    );

    // Get daily request counts for the last 7 days
    const dailyRequests = await pool.query(
      `SELECT DATE(submission_date) as date, COUNT(*) as count 
       FROM laundry_requests 
       WHERE submission_date >= NOW() - INTERVAL '7 days' 
       GROUP BY DATE(submission_date) 
       ORDER BY date DESC`
    );

    res.json({
      status: 'success',
      data: {
        total_clothes: parseInt(totalClothes.rows[0].total) || 0,
        requests_by_status: requestsByStatus.rows,
        daily_requests: dailyRequests.rows
      }
    });
  } catch (error) {
    next(error);
  }
}; 