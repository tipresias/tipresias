// @flow
import React from 'react';
import type { Node } from 'react';
import styled from 'styled-components/macro';
import images from '../../images';

const { isotype } = images;

export const Footer = styled.footer`
  grid-column: 1 / -1;
  background: #f0f3f7;
  border-top: 1px solid #d7d7d7;
  text-align: center;
  font-size: 1rem;
  color: #373a3c;
  a {
    color: #373a3c;
  }
`;

export const Isotype = styled.img`
  height: 20px;
  width: auto;
  fill: #CCCCCC;
`;

const PageFooter = (): Node => (
  <Footer>
    <p>
      <span> Tipresias 2019 - Created in Melbourne by </span>
      <a href="https://github.com/tipresias">Team Tipresias</a>
    </p>
    <p>
      <Isotype src={isotype} alt="Tipresias" />
      <a href="https://gist.github.com/meligatt/72b359279b5da1eb6d75be9a2ae403b0"> logo credits</a>
    </p>
  </Footer>
);

export default PageFooter;
