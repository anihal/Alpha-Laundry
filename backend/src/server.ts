import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import { config } from './config/env';
import { errorHandler } from './middleware/errorHandler';
import { notFoundHandler } from './middleware/notFoundHandler';
import studentRoutes from './routes/studentRoutes';
import adminRoutes from './routes/adminRoutes';
import authRoutes from './routes/authRoutes';

const app = express();

// Middleware
app.use(helmet()); // Security headers
app.use(cors({
  origin: config.api.corsOrigin,
  credentials: true
}));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', environment: config.nodeEnv });
});

// Routes
app.use(`${config.api.prefix}/auth`, authRoutes);
app.use(`${config.api.prefix}/student`, studentRoutes);
app.use(`${config.api.prefix}/admin`, adminRoutes);

// Error handling
app.use(notFoundHandler);
app.use(errorHandler);

// Start server
app.listen(config.port, () => {
  console.log(`✓ Server running on port ${config.port} in ${config.nodeEnv} mode`);
  console.log(`✓ Database: ${config.database.name}@${config.database.host}`);
  console.log(`✓ CORS enabled for: ${config.api.corsOrigin}`);
}); 