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
import { FETCH_CHART_PARAMETERS_QUERY } from '../../graphql';
import {
  AppContainerStyled, MainStyled,
} from './style';
import type { fetchModelsAndYears } from '../../graphql/graphql-types/fetchModelsAndYears';
import { log } from '../../helpers';

const isDarkModeStored = () => localStorage.getItem('isDarkMode') === 'true';

const App = () => {
  const [isDarkMode, setIsDarkMode] = useState(isDarkModeStored());

  const { data, loading, error } = useQuery<fetchModelsAndYears>(FETCH_CHART_PARAMETERS_QUERY);
  if (loading) return <div>Loading Tipresias....</div>;
  if (error) {
    log.error(error);
    return <div>Error: Something happened, try again later.</div>;
  }
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

  const toggleDarkMode = () => {
    if (isDarkModeStored()) {
      setIsDarkMode(false);
      localStorage.setItem('isDarkMode', 'false');
      return;
    }

    setIsDarkMode(true);
    localStorage.setItem('isDarkMode', 'true');
  };

  return (
    <ThemeProvider theme={isDarkMode ? darkTheme : lightTheme}>
      <Router>
        <AppContainerStyled>
          <PageHeader
            links={[{ url: '/about', text: 'About' }]}
            isDarkMode={isDarkMode}
            toggleDarkMode={toggleDarkMode}
          />
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
