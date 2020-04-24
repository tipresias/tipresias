// @flow
import React from 'react';
import type { Node } from 'react';
import styled from 'styled-components/macro';

const FieldsetStyled = styled.fieldset`
display: flex;
flex-wrap: wrap;
`;

const LegendStyled = styled.legend`
  font-weight: bold;
`;

type Props = {
  legend: string,
  children: Node;
}
const Fieldset = ({
  legend,
  children,
}: Props): Node => (
  <FieldsetStyled>
    <LegendStyled>{legend}</LegendStyled>
    {children}
  </FieldsetStyled>
);

export default Fieldset;
