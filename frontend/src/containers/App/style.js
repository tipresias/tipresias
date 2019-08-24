import styled from 'styled-components/macro';

// mobile first app container
export const AppContainerStyled = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  grid-template-rows: 80px auto 80px;
  grid-gap: 5px;
  grid-auto-flow: column;
  background-color: ${props => props.theme.colors.background};
  color: ${props => props.theme.colors.textColor};
  @media (min-width: 768px) {
    grid-template-columns: 40px auto 40px;
    grid-gap: 0.5rem;
  }
`;

export const MainStyled = styled.main`
  grid-column: 1 / -1;
  @media (min-width: 768px) {
    grid-column: 2 / -2;
  }
`;

export const ThemeBarStyled = styled.div`
  font-size: 0.8rem;
`;

export const ToggleThemeButton = styled.button`
  background: ${props => props.theme.colors.buttonBackground};
  color: ${props => props.theme.colors.buttonColor};
  display: block;
  margin-top: 24px;
  max-width: 100%;
  border: none;
  line-height: 36px;
  padding: 0 12px;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  `;
