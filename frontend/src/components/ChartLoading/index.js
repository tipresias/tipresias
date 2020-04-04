// @flow
import React from 'react';
import type { Node } from 'react';
import styled from 'styled-components/macro';

// todo: add a barchart empty animation
const ChartLoadingStyled = styled.div`
  border: 1px solid green;
  background: white;
  height: 300px;
`;

type Props = {
  text: string
}

const ChartLoading = ({ text }: Props): Node => (
  <ChartLoadingStyled>{text}</ChartLoadingStyled>
);

export default ChartLoading;
