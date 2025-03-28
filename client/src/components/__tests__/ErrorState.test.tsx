import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import ErrorState from '../ErrorState';
import { ApiError } from '../../api/errorHandler';

describe('ErrorState', () => {
  const mockError: ApiError = {
    message: 'Test error message',
    code: 'TEST_ERROR',
    status: 500,
  };

  it('renders error message', () => {
    render(<ErrorState error={mockError} />);
    expect(screen.getByText('Test error message')).toBeInTheDocument();
  });

  it('renders retry button when onRetry is provided', () => {
    const onRetry = jest.fn();
    render(<ErrorState error={mockError} onRetry={onRetry} />);
    
    const retryButton = screen.getByText('Try Again');
    expect(retryButton).toBeInTheDocument();
    
    fireEvent.click(retryButton);
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('does not render retry button when onRetry is not provided', () => {
    render(<ErrorState error={mockError} />);
    expect(screen.queryByText('Try Again')).not.toBeInTheDocument();
  });

  it('renders with fullScreen prop', () => {
    const { container } = render(<ErrorState error={mockError} fullScreen />);
    const alertContainer = container.firstChild as HTMLElement;
    expect(alertContainer).toHaveStyle({
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
    });
  });
}); 