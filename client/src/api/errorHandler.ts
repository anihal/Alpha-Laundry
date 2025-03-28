import { AxiosError } from 'axios';

export interface ApiError {
  message: string;
  code?: string;
  status?: number;
}

interface ApiResponse {
  message?: string;
  code?: string;
}

export const handleApiError = (error: AxiosError<ApiResponse>): ApiError => {
  if (error.response) {
    // The request was made and the server responded with a status code
    // that falls out of the range of 2xx
    return {
      message: error.response.data?.message || 'An error occurred',
      code: error.response.data?.code,
      status: error.response.status,
    };
  } else if (error.request) {
    // The request was made but no response was received
    return {
      message: 'No response received from server',
      status: 0,
    };
  } else {
    // Something happened in setting up the request that triggered an Error
    return {
      message: error.message || 'An error occurred',
      status: 0,
    };
  }
};

export const isApiError = (error: unknown): error is ApiError => {
  return (
    typeof error === 'object' &&
    error !== null &&
    'message' in error &&
    typeof (error as ApiError).message === 'string'
  );
}; 