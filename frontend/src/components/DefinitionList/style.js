import styled from 'styled-components/macro';
// DefinitionListStyled, DefinitionTermStyled, DefinitionDescriptionStyled
export const DefinitionListStyled = styled.dl`
  display:flex;
  flex-wrap: wrap;
  border-bottom: 2px solid ${props => props.theme.colors.divisionColor};
`;

export const DefinitionTermStyled = styled.dt`
  width: 40%;
  margin: 0;
  border-top: 2px solid ${props => props.theme.colors.divisionColor};
  font-weight: normal;
  padding: 0.5rem 0;
  &:after {
    content:':';
  }
`;

export const DefinitionDescriptionStyled = styled.dd`
  width: 60%;
  margin-left: auto;
  border-top: 2px solid ${props => props.theme.colors.divisionColor};
  padding: 0.5rem 0;
  text-align: center;
  font-weight: bold;
  font-size: 1.1rem;
  @media (min-width: 425px) {
    text-align: left;
  }
`;
