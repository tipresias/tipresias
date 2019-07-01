// @flow
import React from 'react';
import { Route, BrowserRouter as Router } from 'react-router-dom';
import { Query, Mutation } from 'react-apollo';
// import { gql } from 'apollo-boost';
import PageHeader from '../../components/PageHeader';
import PageFooter from '../../components/PageFooter';
import Dashboard from '../Dashboard';
import Glossary from '../Glossary';
import About from '../About';
import { AppContainerStyled, MainStyled } from './style';
import { SET_THEME_MUTATION, FETCH_THEME } from '../../graphql';

// eslint-disable-next-line react/prefer-stateless-function
class App extends React.Component {
  render() {
    return (
      <Query query={FETCH_THEME}>
        {({ loading, error, data }) => {
          if (loading) return (<p>Loading...</p>);
          if (error) return (<p>Error :( Please try again</p>);
          return (
            <AppContainerStyled theme={data.fetchTheme.name}>
              <Router>
                <PageHeader />
                <MainStyled>
                  <Mutation mutation={SET_THEME_MUTATION}>
                    {
                      (setTheme, { loading, error }) => {
                        if (loading) return (<p>Loading...</p>);
                        if (error) return (<p>Error :( Please try again</p>);
                        return (
                          <div>
                            <label htmlFor="theme1">
                              <input type="radio" value="dark" name="theme" id="theme1" onChange={(e) => { setTheme({ variables: { name: e.target.value } }); }} checked={data.fetchTheme.name === 'dark'} />
                              dark
                            </label>
                            <label htmlFor="theme2">
                              <input type="radio" value="light" name="theme" id="theme2" onChange={(e) => { setTheme({ variables: { name: e.target.value } }); }} checked={data.fetchTheme.name === 'light'} />
                              light
                            </label>
                          </div>
                        );
                      }
                    }
                  </Mutation>
                  <p>{`Current theme is: ${data.fetchTheme.name}`}</p>
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
      </Query>
    );
  }
}

export default App;
