import { css } from 'styled-components';
import styled from 'styled-components/macro';

// AppContainer, Header, Logo, HeaderLinks,
// Widget, WidgetHeading, List, ListItem, Stat, WidgetFooter, Footer

export const AppContainer = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  grid-gap: 5px;
  font-family: sans-serif;
  @media (min-width: 768px) {
    grid-template-columns: 1fr 18% 18% 18% 18% 1fr;
    grid-template-rows: 80px auto auto 100px;
    grid-gap: 20px;
  }
`;


export const WidgetStyles = css`
  grid-column: 1/ -1;
  background-color: #fff;
  border: 1px solid rgba(0, 0, 0, 0.125);
  border-radius: 0.25rem;
  box-shadow: 0 0.25rem 0.75rem rgba(0, 0, 0, 0.05);
  padding: 1.25rem;
  @media (min-width: 768px) {
    grid-column: ${props => props.gridColumn};
  }
`;

export const WidgetHeading = styled.h3`
  font-style: bold;
  font-size: 0.8rem;
  color: #373a3c;
  letter-spacing: 0;
  text-align: left;
`;

export const List = styled.div`
  display: flex;
  flex-direction: column;
`;

export const ListItem = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  border: 1px solid #dddddd;
  border-radius: 4px;
`;

export const Stat = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex: 1;
  padding: 0.5rem;
  &::after {
    content: "|";
    float: right;
    color: rgba(0, 0, 0, 0.125);
  }
  &:last-child::after {
    display: none;
  }
  .key {
    font-size: 1rem;
    color: #373a3c;
  }
  .value {
    font-size: 1.625rem;
    color: #373a3c;
  }
`;

export const WidgetFooter = styled.div`
  padding: 1rem 0.5rem;
`;
