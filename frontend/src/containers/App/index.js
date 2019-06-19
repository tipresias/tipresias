// @flow
import React from 'react';
import { Route, BrowserRouter as Router } from 'react-router-dom';
import PageHeader from '../../components/PageHeader';
import PageFooter from '../../components/PageFooter';
import Dashboard from '../Dashboard';
import Glossary from '../Glossary';
import { AppContainerStyled, MainStyled } from './style';

const App = () => (
  <AppContainerStyled>
    <PageHeader />
    <MainStyled>
      <Router>
        <Route exact path="/" component={Dashboard} />
        <Route exact path="/glossary/:id" component={Glossary} />
      </Router>
    </MainStyled>
    <PageFooter />
  </AppContainerStyled>
);

export default App;
