// @flow
import React from 'react';
import type { Node } from 'react';
import styled from 'styled-components/macro';

const EmptyStatusStyled = styled.div`
  border: 1px solid orange;
  color: orange;
  background: white;
  height: 300px;
`;
const ErrorStatusStyled = styled.div`
  border: 1px solid red;
  color: red;
  background: white;
  height: 300px;
`;

const DefaultStatusStyled = styled.div`
  border: 1px solid gray;
  color: gray;
  background: white;
  height: 300px;
`;

type Props = {
  text: string,
  error?: boolean,
  empty?: boolean
}

const StatusBar = ({ error, empty, text }: Props): Node => {
  if (empty) return <EmptyStatusStyled>{text}</EmptyStatusStyled>;
  if (error) return <ErrorStatusStyled>{text}</ErrorStatusStyled>;
  return <DefaultStatusStyled>{text}</DefaultStatusStyled>;
};

StatusBar.defaultProps = {
  empty: false,
  error: false,
};

export default StatusBar;
