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
  margin-top: 1rem;
  margin-bottom: 1rem;
  background-color: ${props => props.theme.colors.widgetBackground};
  border: 1px solid ${props => props.theme.colors.widgetBorderColor};
  border-radius: 0.25rem;
  box-shadow: ${props => props.theme.colors.widgetBoxShadow};
  padding: 2rem 0.5rem;
  @media (min-width: 768px) {
    grid-column: ${props => props.gridColumn};
    padding: 2rem;
  }
`;

export const WidgetHeading = styled.h3`
  font-style: normal;
  color: ${props => props.theme.colors.textColor};
  letter-spacing: 0;
  margin-top: 0;
  display: flex;
  justify-content: space-between;
`;

export const WidgetSubHeading = styled.h4`
  font-style: normal;
  color: ${props => props.theme.colors.textColor};
  letter-spacing: 0;
  margin-top: 0;
  display: flex;
  justify-content: space-between;
`;

export const WidgetFooter = styled.div`
  padding: 2rem 0.5rem 1rem 0.5rem;
  display: flex;
  align-items: center;
  justify-content: space-evenly;
  flex-wrap: wrap;
`;
