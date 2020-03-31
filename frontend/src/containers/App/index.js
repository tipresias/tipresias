// @flow
import React, { useState } from 'react';
import { Route, BrowserRouter as Router } from 'react-router-dom';
import { useQuery } from '@apollo/react-hooks';
import { ThemeProvider } from 'styled-components';
import darkTheme from '../../themes/dark';
import lightTheme from '../../themes/light';
import PageHeader from '../../components/PageHeader';
import PageFooter from '../../components/PageFooter';
import Dashboard from '../Dashboard';
import Glossary from '../Glossary';
import About from '../About';
import { FETCH_PREDICTION_YEARS_QUERY } from '../../graphql';
import {
  AppContainerStyled, MainStyled, ThemeBarStyled, ToggleThemeButton,
} from './style';

const isDarkModeStored = () => {
  const stored = localStorage.getItem('isDarkMode');
  if (stored === 'true') { return true; } return false;
};

const App = () => {
  const [isDarkMode, setIsDarkMode] = useState(isDarkModeStored());

  const { data, loading, error } = useQuery(FETCH_PREDICTION_YEARS_QUERY);
  if (loading) return <div>Loading....</div>;
  if (error) return <div>Loading....</div>;
  if (data === undefined) return <p>ERROR</p>;

  return (
    <ThemeProvider theme={isDarkMode ? darkTheme : lightTheme}>
      <Router>
        <AppContainerStyled>
          <PageHeader>
            <ThemeBarStyled>
              <ToggleThemeButton
                onClick={() => {
                  if (!isDarkModeStored()) {
                    setIsDarkMode(true);
                    localStorage.setItem('isDarkMode', 'true');
                  } else {
                    setIsDarkMode(false);
                    localStorage.setItem('isDarkMode', 'false');
                  }
                }}
              >
                Toggle Dark Mode
              </ToggleThemeButton>
              <div>
                {`Current theme: ${isDarkMode ? 'Dark' : 'Light'}`}
              </div>
            </ThemeBarStyled>
          </PageHeader>
          <MainStyled>
            <Route exact path="/" render={() => <Dashboard years={data.fetchPredictionYears} defaultModel="tipresias" />} />
            <Route path="/glossary" component={Glossary} />
            <Route exact path="/about" component={About} />
          </MainStyled>
          <PageFooter />
        </AppContainerStyled>
      </Router>
    </ThemeProvider>
  );
};

export default App;
