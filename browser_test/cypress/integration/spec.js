describe("HomePage", function(){
  beforeEach(() => {
    cy.visit("/", { headers: { Connection: "Keep-Alive" } });
    cy.wait(1000);
  });

  it("loads widgets", () => {
    cy.get("h3[class*=WidgetHeading]").should('have.length', 3);
  });

  it("loads chart", () => {
    cy.get(".recharts-responsive-container").should('be.visible');
  });

  it("toggles to dark theme", () => {
    cy.get("button[class*=ToggleThemeButton]").click();
    cy.get("button[class*=ToggleThemeButton]").should('have.css', 'background-color', 'rgb(255, 255, 255)');
  });
});
