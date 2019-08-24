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
  color: ${props => props.theme.colors.textColor};
  a {
    color: ${props => props.theme.colors.textColor};
  }
`;

const Isotype = styled.img`
  height: 18px;
  width: auto;
  margin: 0 5px;
  filter: ${props => props.theme.colors.logoFilter};
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
