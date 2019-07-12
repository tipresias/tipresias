// @flow
import React, { Component } from 'react';
import { Route, BrowserRouter as Router } from 'react-router-dom';
import PageHeader from '../../components/PageHeader';
import PageFooter from '../../components/PageFooter';
import Dashboard from '../Dashboard';
import Glossary from '../Glossary';
import About from '../About';
import { AppContainerStyled, MainStyled } from './style';

// eslint-disable-next-line react/prefer-stateless-function
class App extends Component {
  render() {
    return (
      <AppContainerStyled theme="light">
        <Router>
          <PageHeader />
          <MainStyled>
            {/* <div>
              <label htmlFor="theme1">
                <input type="radio" value="dark" name="theme" id="theme1" onChange={(e) => { setTheme(e.target.value); }} checked={data.fetchTheme.name === 'dark'} />
                dark
              </label>
              <label htmlFor="theme2">
                <input type="radio" value="light" name="theme" id="theme2" onChange={(e) => { setTheme({ variables: { name: e.target.value } }); }} checked={data.fetchTheme.name === 'light'} />
                light
              </label>
            </div> */}
            {/* <p>Current theme is: light</p> */}
            <Route exact path="/" component={Dashboard} />
            <Route path="/glossary" component={Glossary} />
            <Route exact path="/about" component={About} />
          </MainStyled>
          <PageFooter />
        </Router>
      </AppContainerStyled>
    );
  }
}

export default App;
