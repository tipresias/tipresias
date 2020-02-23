it("loads page", () => {
  cy.visit("/", { headers: { Connection: "Keep-Alive" } });
  cy.contains("tipresias performance metrics");
});
