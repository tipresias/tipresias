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
  background-color: ${props => props.theme.colors.widgetBackground};
  border: 1px solid ${props => props.theme.colors.widgetBorderColor};
  border-radius: 0.25rem;
  box-shadow: ${props => props.theme.colors.widgetBoxShadow};
  @media (min-width: 768px) {
    grid-column: ${props => props.gridColumn};
    padding: 3rem;
  }
`;

export const WidgetHeading = styled.h3`
  font-style: normal;
  color: ${props => props.theme.colors.textColor};
  letter-spacing: 0;
  text-align: left;
  margin-top: 0;
`;

export const WidgetFooter = styled.div`
  padding: 1rem 0.5rem;
`;
