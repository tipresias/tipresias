// @flow
import React, { Fragment, useState } from 'react';
import type { Node } from 'react';
import { Query } from '@apollo/react-components';
import styled from 'styled-components/macro';
import {
  FETCH_YEARLY_PREDICTIONS_QUERY,
  FETCH_LATEST_ROUND_PREDICTIONS_QUERY,
  FETCH_LATEST_ROUND_STATS,
} from '../../graphql';
import LineChartMain from '../../components/LineChartMain';
import Select from '../../components/Select';
import ChartLoading from '../../components/ChartLoading';
import StatusBar from '../../components/StatusBar';
import DefinitionList from '../../components/DefinitionList';
import Table from '../../components/Table';
import ErrorBoundary from '../../components/ErrorBoundary';
import {
  WidgetStyles, WidgetHeading, WidgetSubHeading, WidgetFooter, DashboardContainerStyled,
} from './style';
import { dataTransformer } from './dataTransformer';
import type { ModelType } from '../../types';

type DashboardProps = {
  models: Array<ModelType>,
  years: Array<number>
};

const Widget = styled.div`${WidgetStyles}`;

const Dashboard = ({ years, models }: DashboardProps) => {
  const [defaultModel] = models.filter(item => item.isPrinciple);

  const latestYear = years[years.length - 1];
  const [year, setYear] = useState(latestYear);

  const initialSelectedModels = models.map(item => item.name);
  const [checkedModels, setSelectedModels] = useState(initialSelectedModels);


  return (
    <ErrorBoundary>
      <DashboardContainerStyled>
        <Widget gridColumn="1 / -1">
          <WidgetHeading>
            Cumulative accuracy by round
            {year && <div className="WidgetHeading__selected-year">{`year: ${year}`}</div>}
          </WidgetHeading>
          <Query query={FETCH_YEARLY_PREDICTIONS_QUERY} variables={{ year }}>
            {(response: any): Node => {
              const { loading, error, data } = response;
              if (loading) return <ChartLoading text="Brrrrr ..." />;
              if (error) return <StatusBar text={error.message} error />;
              if (data.fetchYearlyPredictions.predictionsByRound.length === 0) {
                return <StatusBar text="No data found" empty />;
              }
              return (
                <LineChartMain
                  models={checkedModels}
                  data={data.fetchYearlyPredictions.predictionsByRound}
                />
              );
            }}
          </Query>
          <WidgetFooter>
            <Select
              id="year"
              label="Choose a year"
              name="year"
              value={year}
              onChange={(event: SyntheticEvent<HTMLSelectElement>): void => {
                setYear(parseInt(event.currentTarget.value, 10));
              }}
              options={years}
            />
            <fieldset style={{ display: 'flex', flexWrap: 'wrap' }}>
              <legend>Choose a model:</legend>
              {
                initialSelectedModels.map((modelName) => {
                  const labelName = modelName.replace(/_/g, ' ');
                  return (
                    <label htmlFor={modelName} key={modelName} style={{ marginRight: '2rem' }}>
                      <input
                        type="checkbox"
                        id={modelName}
                        name={modelName}
                        value={modelName}
                        checked={checkedModels.includes(modelName)}
                        onChange={(event: SyntheticEvent<HTMLSelectElement>): void => {
                          const checkedModel = event.currentTarget.value;
                          if (checkedModels.includes(checkedModel)) {
                            const updatedModels = checkedModels.filter(
                              item => item !== checkedModel,
                            );
                            setSelectedModels(updatedModels);
                          } else {
                            setSelectedModels([...checkedModels, checkedModel]);
                          }
                        }}
                      />
                      {labelName}
                    </label>
                  );
                })
              }
            </fieldset>
          </WidgetFooter>
        </Widget>

        <Widget gridColumn="1 / -1" style={{ overflowX: 'scroll' }}>
          <WidgetHeading>Predictions</WidgetHeading>
          <Query query={FETCH_LATEST_ROUND_PREDICTIONS_QUERY}>
            {(response: any): Node => {
              const { loading, error, data } = response;
              if (loading) return <p>Brrrrrr...</p>;
              if (error) return <StatusBar text={error.message} error />;
              if (data.fetchLatestRoundPredictions.matches.length === 0) {
                return (
                  <StatusBar
                    text="No data found"
                    empty
                  />
                );
              }

              const { roundNumber } = data.fetchLatestRoundPredictions;
              const { matches } = data.fetchLatestRoundPredictions;
              const rowsArray = dataTransformer(matches, defaultModel.name);

              if (rowsArray.length === 0) {
                return <StatusBar text="No data available." error />;
              }
              const caption = `${defaultModel.name} predictions for matches of round ${roundNumber}, season ${latestYear}`;
              return (
                <Table
                  caption={caption}
                  headers={['Date', 'Predicted Winner', 'Predicted margin', 'Win probability', 'is Correct?']}
                  rows={rowsArray}
                />
              );
            }}
          </Query>
        </Widget>

        <Widget gridColumn="1 / -2">
          <Query
            query={FETCH_LATEST_ROUND_STATS}
            variables={{ latestYear, roundNumber: -1, mlModelName: defaultModel.name }}
          >
            {(response: any): Node => {
              const { loading, error, data } = response;
              if (loading) return <p>Brrrrr...</p>;
              if (error) return <StatusBar text={error.message} error />;
              const { seasonYear, predictionsByRound } = data.fetchYearlyPredictions;
              const { roundNumber, modelMetrics } = predictionsByRound[0];
              const {
                modelName,
                cumulativeCorrectCount,
                cumulativeMarginDifference,
                cumulativeMeanAbsoluteError,
              } = modelMetrics[0];

              return (
                <Fragment>
                  <WidgetHeading>
                    {`Performance metrics for ${modelName}`}
                  </WidgetHeading>
                  <WidgetSubHeading>{`Round ${roundNumber},  Season ${seasonYear} `}</WidgetSubHeading>
                  <DefinitionList items={[
                    {
                      id: 1,
                      key: 'Cumulative Correct Count',
                      value: Math.round(cumulativeCorrectCount * 100) / 100,
                    },
                    {
                      id: 2,
                      key: 'Cumulative Mean Absolute Error (MAE)',
                      value: Math.round(cumulativeMeanAbsoluteError * 100) / 100,
                    },
                    {
                      id: 3,
                      key: 'Cumulative Margin Difference',
                      value: Math.round(cumulativeMarginDifference * 100) / 100,
                    },
                  ]}
                  />
                </Fragment>
              );
            }}
          </Query>
        </Widget>
      </DashboardContainerStyled>
    </ErrorBoundary>
  );
};
export default Dashboard;
