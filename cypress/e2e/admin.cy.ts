describe('Admin Flow', () => {
  beforeEach(() => {
    // Reset the database state before each test
    cy.exec('npm run db:reset');
  });

  it('should allow an admin to login and view dashboard', () => {
    // Login as an admin
    cy.loginAsAdmin('admin', 'admin123');
    
    // Verify we're on the admin dashboard
    cy.url().should('include', '/admin/dashboard');
    
    // Check dashboard stats
    cy.get('[data-testid="total-requests"]').should('be.visible');
    cy.get('[data-testid="completed-requests"]').should('be.visible');
    cy.get('[data-testid="total-clothes"]').should('be.visible');
  });

  it('should allow an admin to update request status', () => {
    // First, create a request as a student
    cy.loginAsStudent('STUDENT001', 'password123');
    cy.get('[data-testid="submit-request-button"]').click();
    cy.submitLaundryRequest(5);
    cy.get('[data-testid="request-success"]').should('be.visible');
    
    // Then login as admin
    cy.loginAsAdmin('admin', 'admin123');
    
    // Find the request in the pending requests list
    cy.get('[data-testid="pending-requests"]')
      .should('contain', 'STUDENT001')
      .and('contain', '5');
    
    // Update the status
    cy.get('[data-testid="update-status-button"]').first().click();
    cy.get('[data-testid="status-select"]').select('processing');
    cy.get('[data-testid="confirm-status-update"]').click();
    
    // Verify the status was updated
    cy.get('[data-testid="pending-requests"]')
      .should('not.contain', 'STUDENT001');
  });

  it('should show analytics data', () => {
    cy.loginAsAdmin('admin', 'admin123');
    
    // Check if analytics chart is visible
    cy.get('[data-testid="requests-by-status-chart"]').should('be.visible');
    
    // Check if chart has data
    cy.get('[data-testid="requests-by-status-chart"]')
      .find('path')
      .should('have.length.greaterThan', 0);
  });
}); 