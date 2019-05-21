// @flow
import React from 'react';
import type { Node } from 'react';
import styled from 'styled-components/macro';
import images from '../../images';

const { logo } = images;

export const Header = styled.header`
  grid-column: 1 / -1;
  display:flex;
  position relative;
  align-items: center;
  justify-content: center;
  background-color: white;
  border-bottom: 1px solid rgba(0,0,0,.125);
  @media (min-width: 768px) {
    grid-column: 2 / -2;
  }
`;

export const Logo = styled.img`
  height: auto;
  width: 150px;
`;

export const HeaderLinks = styled.div`
  position: absolute;
  right: 0;
  a {
    font-size: 1rem;
    color: rgba(0, 0, 0, 0.3);
    padding: 0.5rem;
  }
`;

const links = [{ url: 'https://github.com/tipresias', text: 'About' }];

const PageHeader = (): Node => (
  <Header>
    <Logo src={logo} alt="Tipresias" width="120" />
    <HeaderLinks>
      {
        links.map(link => <a key={link.url} href={link.url}>{link.text}</a>)
      }
    </HeaderLinks>
  </Header>
);

export default PageHeader;
