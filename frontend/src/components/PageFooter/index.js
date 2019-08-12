// @flow
import React from 'react';
import type { Node } from 'react';
import styled from 'styled-components/macro';
import images from '../../images';

const { isotype } = images;

const Footer = styled.footer`
  grid-column: 1 / -1;
  text-align: center;
  font-size: 1rem;
  color: #373a3c;
  a {
    color: #373a3c;
  }
`;

const Isotype = styled.img`
  height: 18px;
  width: auto;
  margin: 0 5px;
`;

const PageFooter = (): Node => (
  <Footer>
    <a href="https://github.com/tipresias">Tipresias 2019</a>
    <div>
      <Isotype src={isotype} alt="Tipresias" />
      <a href="https://gist.github.com/meligatt/72b359279b5da1eb6d75be9a2ae403b0">credits</a>
    </div>
  </Footer>
);

export default PageFooter;
