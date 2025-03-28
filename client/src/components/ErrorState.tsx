import React from 'react';
import { Box, Typography, Button, Alert } from '@mui/material';
import { ApiError } from '../api/errorHandler';

interface ErrorStateProps {
  error: ApiError;
  onRetry?: () => void;
  fullScreen?: boolean;
}

const ErrorState: React.FC<ErrorStateProps> = ({ 
  error, 
  onRetry, 
  fullScreen = false 
}) => {
  const content = (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 2,
        p: 3,
        ...(fullScreen && {
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          bgcolor: 'background.paper',
          zIndex: 9999,
        }),
      }}
    >
      <Alert severity="error" sx={{ width: '100%', maxWidth: 400 }}>
        {error.message}
      </Alert>
      {onRetry && (
        <Button
          variant="contained"
          onClick={onRetry}
          sx={{ mt: 2 }}
        >
          Try Again
        </Button>
      )}
    </Box>
  );

  return content;
};

export default ErrorState; 