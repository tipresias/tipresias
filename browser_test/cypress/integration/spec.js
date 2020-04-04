describe("HomePage", function(){
  beforeEach(() => {
    cy.visit("/", { headers: { Connection: "Keep-Alive" } });
  });

  it("loads page", () => {
    // Need to extend timeout, because the query that fetches this data
    // is a bit slower
    cy.contains("PERFORMANCE METRICS FOR TIPRESIAS_2020", {timeout: 10000});
    cy.contains("PREDICTIONS", {timeout: 10000});
    cy.contains("CUMULATIVE ACCURACY BY ROUND", {timeout: 10000});
  });

  it("toggles to dark theme", () => {
    cy.get("button[class*=ToggleThemeButton]").click();
  });
});
