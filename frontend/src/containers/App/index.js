// @flow
import React, { useState } from 'react';
import { Route, BrowserRouter as Router } from 'react-router-dom';
import { useQuery } from '@apollo/react-hooks';
import { ThemeProvider } from 'styled-components';
import type { Node } from 'react';
import darkTheme from '../../themes/dark';
import lightTheme from '../../themes/light';
import PageHeader from '../../components/PageHeader';
import PageFooter from '../../components/PageFooter';
import Dashboard from '../Dashboard';
import Glossary from '../Glossary';
import About from '../About';
import { FETCH_CHART_PARAMETERS_QUERY } from '../../graphql';
import {
  AppContainerStyled, MainStyled, ToggleThemeButton,
} from './style';
import type { fetchModelsAndYears } from '../../graphql/graphql-types/fetchModelsAndYears';

const isDarkModeStored = () => {
  const stored = localStorage.getItem('isDarkMode');
  if (stored === 'true') { return true; } return false;
};

const App = (): Node => {
  const [isDarkMode, setIsDarkMode] = useState(isDarkModeStored());

  const { data, loading, error } = useQuery<fetchModelsAndYears>(FETCH_CHART_PARAMETERS_QUERY);
  if (loading) return <div>Loading Tipresias....</div>;
  if (error) return <div>Error: Something happened, try again later.</div>;
  if (data === undefined) return <p>Error: Data not defined.</p>;

  const {
    fetchSeasonPerformanceChartParameters: {
      availableSeasons,
      availableMlModels,
    },
  } = data;


  const metrics = [
    'cumulativeAccuracy',
    'cumulativeBits',
    'cumulativeMeanAbsoluteError',
    'cumulativeCorrectCount',
  ];


  return (
    <ThemeProvider theme={isDarkMode ? darkTheme : lightTheme}>
      <Router>
        <AppContainerStyled>
          <PageHeader links={[{ url: '/about', text: 'About' }]}>
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
            <Route
              exact
              path="/"
              render={() => (
                <Dashboard
                  years={availableSeasons}
                  models={availableMlModels}
                  metrics={metrics}
                />
              )}
            />
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
