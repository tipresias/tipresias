describe("smoke tests", () => {
  it("should allow you to visit the homepage", () => {
    cy.visitAndCheck("/");
  });
});
