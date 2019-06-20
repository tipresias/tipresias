import styled from 'styled-components/macro';

// mobile first app container
export const AppContainerStyled = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  grid-template-rows: 80px auto 80px;
  grid-gap: 5px;
  grid-auto-flow: column;
  font-family: sans-serif;
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
