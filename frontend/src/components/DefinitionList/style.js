import styled from 'styled-components/macro';
// DefinitionListStyled, DefinitionTermStyled, DefinitionDescriptionStyled
export const DefinitionListStyled = styled.dl`
  display:flex;
  flex-wrap: wrap;
  border-bottom: 1px solid #DDDDDD;
`;

export const DefinitionTermStyled = styled.dt`
  width: 30%;
  margin: 0;
  border-top: 1px solid #DDDDDD;
  font-weight: bold;
  padding: 0.5rem 0;
  &:after {
    content:':';
  }
`;

export const DefinitionDescriptionStyled = styled.dd`
  width: 70%;
  margin-left: auto;
  border-top: 1px solid #DDDDDD;
  padding: 0.5rem 0;
`;
