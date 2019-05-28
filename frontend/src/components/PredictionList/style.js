import { css } from 'styled-components';
import styled from 'styled-components/macro';

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

export const StatStyles = css`
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex: 1;
  padding: 0.5rem;
  background-color: ${props => (props.isHighlighted ? 'yellow' : 'white')};
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
