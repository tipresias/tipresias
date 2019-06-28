// @flow
import React from 'react';
import { Route, BrowserRouter as Router } from 'react-router-dom';
import { Query } from 'react-apollo';
import { gql } from 'apollo-boost';
import PageHeader from '../../components/PageHeader';
import PageFooter from '../../components/PageFooter';
import Dashboard from '../Dashboard';
import Glossary from '../Glossary';
import About from '../About';
import { AppContainerStyled, MainStyled } from './style';
import { GET_THEME } from '../../graphql';

class App extends React.Component {
  setTheme = (themeName) => {
    const { client } = this.props;
    console.log(themeName, client);

    // client.mutate({
    //   mutation: gql`
    //     mutation SetTheme($themeName: string){
    //       setTheme(themeName: $themeName) @client {
    //         value
    //       }
    //     }
    //   `,
    //   variables: { themeName },
    // });
  }

  render() {
    return (
      <Query query={GET_THEME}>
        {({ data }) => (
          <AppContainerStyled theme={data.themeName}>
            <Router>
              <PageHeader />
              <MainStyled>
                <div>
                  <label htmlFor="theme1">
                    <input type="radio" value="dark" name="theme" id="theme1" onChange={e => this.setTheme(e.target.value)} />
                    dark
                  </label>
                  <label htmlFor="theme2">
                    <input type="radio" value="light" name="theme" id="theme2" onChange={e => this.setTheme(e.target.value)} />
                    light
                  </label>
                </div>
                <p>{`theme is: ${data.themeName}`}</p>
                <Route exact path="/" component={Dashboard} />
                <Route path="/glossary" component={Glossary} />
                <Route exact path="/about" component={About} />
              </MainStyled>
              <PageFooter />
            </Router>
          </AppContainerStyled>
        )
        }
      </Query>
    );
  }
}

export default App;
