it("loads page", () => {
  cy.visit("/", { headers: { Connection: "Keep-Alive" } });
  // Need to extend timeout, because the query that fetches this data
  // is a bit slower
  cy.contains("performance metrics", {timeout: 10000});
});
