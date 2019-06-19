import styled from 'styled-components/macro';

// mobile first app container
export const AppContainerStyled = styled.div`
  outline: 1px solid blue;
  display: grid;
  grid-template-columns: 1fr;
  grid-gap: 5px;
  font-family: sans-serif;
  @media (min-width: 768px) {
    grid-template-columns: 1fr auto 1fr;
    grid-template-rows: 80px auto 80px;
    grid-gap: 20px;
  }
`;

export const MainStyled = styled.main`
  border: 1px solid green;
  grid-column: 1 / -1;
  @media (min-width: 768px) {
    grid-column: 2 / -2;
  }
`;
