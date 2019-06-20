// @flow
import React from 'react';
import type { Node } from 'react';
import styled from 'styled-components/macro';

// todo: add a barchart empty animation
const BarChartLoadingStyled = styled.div`
  border: 1px solid green;
  background: white;
  height: 300px;
`;

type Props = {
  text: string
}

const BarChartLoading = ({ text }: Props): Node => (
  <BarChartLoadingStyled>{text}</BarChartLoadingStyled>
);

export default BarChartLoading;
