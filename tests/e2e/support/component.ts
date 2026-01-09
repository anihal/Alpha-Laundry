import '@testing-library/cypress/add-commands';
import { mount } from '@cypress/react18';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Create a new QueryClient for testing
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

// Custom mount function that wraps components with necessary providers
Cypress.Commands.add('mountWithProviders', (component: React.ReactNode) => {
  const wrappedComponent = (
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  );
  return mount(wrappedComponent);
});

declare global {
  namespace Cypress {
    interface Chainable {
      mountWithProviders(component: React.ReactNode): Chainable<ReturnType<typeof mount>>;
    }
  }
} 