import '@testing-library/cypress/add-commands';

// Custom command to login as a student
Cypress.Commands.add('loginAsStudent', (studentId: string, password: string) => {
  cy.visit('/login');
  cy.get('input[name="username"]').type(studentId);
  cy.get('input[name="password"]').type(password);
  cy.get('button[type="submit"]').click();
});

// Custom command to login as an admin
Cypress.Commands.add('loginAsAdmin', (username: string, password: string) => {
  cy.visit('/login');
  cy.get('input[name="username"]').type(username);
  cy.get('input[name="password"]').type(password);
  cy.get('button[type="submit"]').click();
});

// Custom command to submit a laundry request
Cypress.Commands.add('submitLaundryRequest', (numClothes: number) => {
  cy.get('input[name="num_clothes"]').type(numClothes.toString());
  cy.get('button[type="submit"]').click();
});

declare global {
  namespace Cypress {
    interface Chainable {
      loginAsStudent(studentId: string, password: string): Chainable<void>;
      loginAsAdmin(username: string, password: string): Chainable<void>;
      submitLaundryRequest(numClothes: number): Chainable<void>;
    }
  }
} 