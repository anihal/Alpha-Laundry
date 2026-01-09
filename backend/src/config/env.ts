import dotenv from 'dotenv';
import { join } from 'path';

// Load environment variables
dotenv.config({ path: join(__dirname, '../../.env') });

interface EnvironmentConfig {
  // Server
  port: number;
  nodeEnv: string;

  // Database
  database: {
    host: string;
    port: number;
    name: string;
    user: string;
    password: string;
  };

  // JWT
  jwt: {
    secret: string;
    expiresIn: string;
  };

  // API
  api: {
    prefix: string;
    corsOrigin: string;
  };
}

/**
 * Validates and returns environment configuration
 * Throws error if required variables are missing
 */
function getConfig(): EnvironmentConfig {
  const requiredVars = [
    'DB_HOST',
    'DB_NAME',
    'DB_USER',
    'DB_PASSWORD',
    'JWT_SECRET'
  ];

  // Check for missing required variables
  const missing = requiredVars.filter(varName => !process.env[varName]);

  if (missing.length > 0) {
    throw new Error(
      `Missing required environment variables: ${missing.join(', ')}\n` +
      `Please copy .env.template to .env and configure all required values.`
    );
  }

  // Validate JWT secret length
  const jwtSecret = process.env.JWT_SECRET!;
  if (jwtSecret.length < 32) {
    console.warn(
      '⚠️  WARNING: JWT_SECRET should be at least 32 characters for security. ' +
      'Current length: ' + jwtSecret.length
    );
  }

  return {
    port: parseInt(process.env.PORT || '3001', 10),
    nodeEnv: process.env.NODE_ENV || 'development',

    database: {
      host: process.env.DB_HOST!,
      port: parseInt(process.env.DB_PORT || '5432', 10),
      name: process.env.DB_NAME!,
      user: process.env.DB_USER!,
      password: process.env.DB_PASSWORD!,
    },

    jwt: {
      secret: jwtSecret,
      expiresIn: process.env.JWT_EXPIRES_IN || '24h',
    },

    api: {
      prefix: process.env.API_PREFIX || '/api',
      corsOrigin: process.env.CORS_ORIGIN || 'http://localhost:3000',
    },
  };
}

// Export singleton config instance
export const config = getConfig();

// Export for testing or advanced use cases
export { getConfig };
