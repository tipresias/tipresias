import { css } from 'styled-components';
import styled from 'styled-components/macro';

export const DashboardContainerStyled = styled.div`
  display:grid;
  grid-template-columns: 1fr;
  grid-gap: 0.2rem;
  @media (min-width: 768px) {
    grid-template-columns: 1fr 1fr 1fr 1fr;
    grid-gap: 1rem;
  }
`;

export const WidgetStyles = css`
  margin-top: 2rem;
  background-color: #fff;
  border-radius: 0.25rem;
  box-shadow: 0 0.3rem 0.25rem rgba(0,0,0,0.05);
  @media (min-width: 768px) {
    grid-column: ${props => props.gridColumn};
    padding: 1rem;
  }
`;

export const WidgetHeading = styled.h3`
  font-style: normal;
  color: #373a3c;
  letter-spacing: 0;
  text-align: left;
`;

export const WidgetFooter = styled.div`
  padding: 1rem 0.5rem;
`;
