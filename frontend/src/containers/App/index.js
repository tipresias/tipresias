// @flow
import React from 'react';
import { Route, Link, BrowserRouter as Router } from 'react-router-dom';
import PageHeader from '../../components/PageHeader';
import PageFooter from '../../components/PageFooter';
import Dashboard from '../Dashboard';
// import Glossary from '../Glossary';
import About from '../About';
import { AppContainerStyled, MainStyled } from './style';

const Topic = ({ match }) => (
  <div>
    <h3>
      Requested Param:
      {match.params.id}
    </h3>
  </div>
);

const Glossary = ({ match }) => {
  console.log('match >>>', match.url);

  return (
    <div>
      <h2>Topics</h2>

      <ul>
        <li>
          <Link to="/glossary/1">Tip point</Link>
        </li>
        <li>
          <Link to="/glossary/2">predicted margin</Link>
        </li>
      </ul>

      <Route path="/glossary/:id" component={Topic} />
    </div>
  );
};
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
