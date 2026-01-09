describe('Student Flow', () => {
  beforeEach(() => {
    // Reset the database state before each test
    cy.exec('npm run db:reset');
  });

  it('should allow a student to login and submit a laundry request', () => {
    // Login as a student
    cy.loginAsStudent('STUDENT001', 'password123');
    
    // Verify we're on the dashboard
    cy.url().should('include', '/student/dashboard');
    
    // Check initial quota
    cy.get('[data-testid="remaining-quota"]').should('contain', '30');
    
    // Submit a laundry request
    cy.get('[data-testid="submit-request-button"]').click();
    cy.submitLaundryRequest(5);
    
    // Verify the request was submitted
    cy.get('[data-testid="request-success"]').should('be.visible');
    
    // Check updated quota
    cy.get('[data-testid="remaining-quota"]').should('contain', '25');
    
    // Verify request appears in history
    cy.get('[data-testid="request-history"]')
      .should('contain', '5')
      .and('contain', 'submitted');
  });

  it('should show error when submitting more clothes than quota', () => {
    cy.loginAsStudent('STUDENT001', 'password123');
    
    // Try to submit more clothes than quota
    cy.get('[data-testid="submit-request-button"]').click();
    cy.submitLaundryRequest(35);
    
    // Verify error message
    cy.get('[data-testid="request-error"]')
      .should('be.visible')
      .and('contain', 'exceeds your remaining quota');
  });

  it('should show loading state while submitting request', () => {
    cy.loginAsStudent('STUDENT001', 'password123');
    
    // Submit a request
    cy.get('[data-testid="submit-request-button"]').click();
    cy.submitLaundryRequest(5);
    
    // Verify loading state
    cy.get('[data-testid="request-loading"]').should('be.visible');
    
    // Wait for loading to complete
    cy.get('[data-testid="request-success"]').should('be.visible');
  });
}); 