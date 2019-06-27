// @flow
import React from 'react';
import { Route, BrowserRouter as Router } from 'react-router-dom';
import PageHeader from '../../components/PageHeader';
import PageFooter from '../../components/PageFooter';
import Dashboard from '../Dashboard';
import Glossary from '../Glossary';
import About from '../About';
import { AppContainerStyled, MainStyled } from './style';

const App = () => (
  <AppContainerStyled>
    <Router>
      <PageHeader />
      <MainStyled>
        <Route exact path="/" component={Dashboard} />
        <Route path="/glossary" component={Glossary} />
        <Route exact path="/about" component={About} />
      </MainStyled>
      <PageFooter />
    </Router>
  </AppContainerStyled>
);

export default App;
