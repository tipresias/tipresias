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
import { FETCH_MODELS_AND_YEARS_QUERY } from '../../graphql';
import {
  AppContainerStyled, MainStyled, ToggleThemeButton,
} from './style';

const isDarkModeStored = () => {
  const stored = localStorage.getItem('isDarkMode');
  if (stored === 'true') { return true; } return false;
};

const App = () => {
  const [isDarkMode, setIsDarkMode] = useState(isDarkModeStored());

  const { data, loading, error } = useQuery(FETCH_MODELS_AND_YEARS_QUERY);
  if (loading) return <div>Loading Tipresias....</div>;
  if (error) return <div>Error: Something happened, try again later.</div>;
  if (data === undefined) return <p>Error: Data not defined.</p>;


  const metrics = ['cumulativeAccuracy', 'cumulativeBits', 'cumulativeMeanAbsoluteError'];


  return (
    <ThemeProvider theme={isDarkMode ? darkTheme : lightTheme}>
      <Router>
        <AppContainerStyled>
          <PageHeader>
            <ToggleThemeButton
              aria-pressed={isDarkMode}
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
              Dark theme:
              <span aria-hidden="true">{isDarkMode ? 'On' : 'Off'}</span>
            </ToggleThemeButton>


          </PageHeader>
          <MainStyled>
            <Route exact path="/" render={() => <Dashboard years={data.fetchPredictionYears} models={data.fetchMlModels} metrics={metrics} />} />
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
