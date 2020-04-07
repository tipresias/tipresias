describe("HomePage", function(){
  beforeEach(() => {
    cy.visit("/", { headers: { Connection: "Keep-Alive" } });
    cy.wait(1000);
  });

  describe("When page loads", () => {
    it("loads all 3 widgets", () => {
      cy.get("h3[class*=WidgetHeading]").should('have.length', 3);
    });

    it("checks all models by defaults", () => {
      cy.get('input[type=checkbox]').should('be.checked');
    });

    it("loads main chart", () => {
      cy.get(".WidgetHeading__selected-year").should('be.visible');
      cy.get(".recharts-responsive-container").should('be.visible');
    });

    it("theme is light by default", () => {
      cy.get("button[class*=ToggleThemeButton]").contains('Off');
    });
  });

  describe("Theme switcher", () => {
    it("toggles to dark theme", () => {
      cy.get("button[class*=ToggleThemeButton]").click();
      cy.get("button[class*=ToggleThemeButton]").contains('On');
      cy.get("[class*=AppContainerStyled]").should('have.css', 'background-color', 'rgb(21, 32, 43)');
    });
  })

  describe("Main chart widget", () => {
    it("refreshes when year is selected", () => {
      cy.get("select").select('2019').should('have.value', '2019');
      cy.get(".WidgetHeading__selected-year").contains('year: 2019');
      cy.get(".recharts-responsive-container").should('be.visible');
    });

    it("refreshes when models are unchecked", () => {
      cy.get("[type=checkbox]").uncheck();
      cy.get(".recharts-responsive-container").should('be.visible');
      cy.get(".recharts-default-legend").should('not.be.visible');
    });

  });
});
