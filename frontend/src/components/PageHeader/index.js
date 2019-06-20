// @flow
import React from 'react';
import type { Node } from 'react';
import { Link } from 'react-router-dom';
import styled from 'styled-components/macro';
import images from '../../images';

const { logo } = images;

const Header = styled.header`
  grid-column: 1 / -1;
  position relative;
  background-color: white;
  border-bottom: 1px solid rgba(0,0,0,.125);
  display: flex;
  justify-content: space-around;
  @media (min-width: 768px) {
    grid-column: 2 / -2;
    align-items: center;
    flex-direction: column;
  }
`;

const Logo = styled.img`
  height: auto;
  width: 90px;
  @media (min-width: 768px){
    width: 160px;
  }
`;

const NavStyled = styled.nav`
  position: absolute;
  left: 0;
  right: 0;
  top: 33px;
  @media (min-width: 768px){
    position: initial;
    top: initial;
    margin-left: 0;
    position: absolute;
  }`;

const ListStyled = styled.ul`
  display: table;
  width: 100%;
  padding: 0;
  margin: 0;
  list-style: none;
`;

const ListItem = styled.li`
  display: table-cell;
  text-align: center;
  @media (min-width: 768px){
    display: inline-block;
  }
`;

const TextLink = styled.a`
  line-height: 48px;
  display: inline-block;
  font-size: 1rem;
  color: rgba(0, 0, 0, 0.3);
  @media (min-width: 768px){
    line-height: 72px;
    padding: 0 16px;
  }
`;

const links = [
  { url: '/about', text: 'About' },
  { url: '/glossary', text: 'Glossary' },
];

const PageHeader = (): Node => (
  <Header>
    <Link to="/">
      <Logo src={logo} alt="Tipresias" width="120" />
    </Link>
    <NavStyled>
      <ListStyled>
        {
          links.map(link => <ListItem key={link.url}><TextLink href={link.url}>{link.text}</TextLink></ListItem>)
        }
      </ListStyled>
    </NavStyled>
  </Header>
);

export default PageHeader;
