// @flow
import React, { Fragment, useState } from 'react';
import type { Node } from 'react';
import { Query } from '@apollo/react-components';
import styled from 'styled-components/macro';
import {
  FETCH_YEARLY_PREDICTIONS_QUERY,
  FETCH_LATEST_ROUND_PREDICTIONS_QUERY,
} from '../../graphql';
import type { fetchYearlyPredictions } from '../../graphql/graphql-types/fetchYearlyPredictions';
import type { fetchLatestRoundPredictions } from '../../graphql/graphql-types/fetchLatestRoundPredictions';
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
import dataTransformerTable from './dataTransformerTable';
import dataTransformerLineChart from './dataTransformerLineChart';

export type ModelType = {
  name: string,
  forCompetition: boolean,
  isPrinciple: boolean
}

type DashboardProps = {
  metrics: Array<string>,
  models: Array<ModelType>,
  years: Array<number>
};

interface fetchYearlyPredictionsResponse {
  loading: any;
  error: any;
  data: fetchYearlyPredictions;
}

interface fetchLatestRoundPredictionsResponse {
  loading: any;
  error: any;
  data: fetchLatestRoundPredictions;
}

const Widget = styled.div`${WidgetStyles}`;

const Dashboard = ({ years, models, metrics }: DashboardProps) => {
  const [principleModel] = models.filter(item => item.isPrinciple);

  const latestYear = years[years.length - 1];
  const [year, setYear] = useState(latestYear);

  const initialSelectedModels = models.map(item => item.name);
  const [checkedModels, setSelectedModels] = useState(initialSelectedModels);

  const [currentMetric, setCurrentMetric] = useState(metrics[0]);
  const currentMetricLabel = currentMetric.replace(/cumulative/g, '');
  const mainWidgetTitle = `Cumulative ${currentMetricLabel} by round`;
  return (
    <ErrorBoundary>
      <DashboardContainerStyled>
        <Widget gridColumn="1 / -1">
          <WidgetHeading>
            {mainWidgetTitle}
            {year && <div className="WidgetHeading__selected-year">{`year: ${year}`}</div>}
          </WidgetHeading>
          <Query
            query={
              FETCH_YEARLY_PREDICTIONS_QUERY
            }
            variables={{
              year,
              forCompetitionOnly: false,
            }}
          >
            {({ loading, error, data }: fetchYearlyPredictionsResponse): Node => {
              if (loading) return <ChartLoading text="Brrrrr ..." />;
              if (error) return <StatusBar text={error.message} error />;
              const { predictionsByRound: predictionsByRoundData } = data.fetchYearlyPredictions;

              if (predictionsByRoundData.length === 0) {
                return <StatusBar text="No data found" empty />;
              }
              const metric = { name: currentMetric, label: currentMetricLabel };
              const dataTransformed = dataTransformerLineChart(predictionsByRoundData, metric);

              return (
                <LineChartMain
                  models={checkedModels}
                  metric={metric}
                  data={dataTransformed}
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
                    <label htmlFor={modelName} key={modelName} style={{ margin: '0.5rem 0' }}>
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
            <fieldset style={{ display: 'flex', flexWrap: 'wrap' }}>
              <legend>Choose a metric:</legend>
              {
                metrics.map((metricName) => {
                  const labelName = metricName.replace(/cumulative/g, '');
                  return (
                    <label htmlFor={metricName} key={metricName} style={{ margin: '0.5rem 0' }}>
                      <input
                        type="radio"
                        id={metricName}
                        name={metricName}
                        value={metricName}
                        checked={metricName === currentMetric}
                        onChange={(event: SyntheticEvent<HTMLSelectElement>): void => {
                          const checkedMetric = event.currentTarget.value;
                          setCurrentMetric(checkedMetric);
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
            {({ loading, error, data }: fetchLatestRoundPredictionsResponse): Node => {
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
              const rowsArray = dataTransformerTable(matches, principleModel.name);

              if (rowsArray.length === 0) {
                return <StatusBar text="No data available." error />;
              }
              const caption = `${principleModel.name} predictions for matches of round ${roundNumber}, season ${latestYear}`;
              return (
                <Table
                  caption={caption}
                  headers={['Date', 'Predicted Winner', 'Predicted margin', 'Win probability (%)', 'is Correct?']}
                  rows={rowsArray}
                />
              );
            }}
          </Query>
        </Widget>

        <Widget gridColumn="1 / -2">
          <Query
            query={FETCH_YEARLY_PREDICTIONS_QUERY}
            variables={{ year: latestYear, roundNumber: -1, forCompetitionOnly: true }}
          >
            {({ loading, error, data }: fetchYearlyPredictionsResponse): Node => {
              if (loading) return <p>Brrrrr...</p>;
              if (error) return <StatusBar text={error.message} error />;
              const { seasonYear, predictionsByRound } = data.fetchYearlyPredictions;
              const { roundNumber, modelMetrics } = predictionsByRound[0];


              // cumulativeCorrectCount
              const { cumulativeCorrectCount } = modelMetrics.find(
                item => (item.modelName === principleModel.name),
              ) || {};

              // bits
              const { cumulativeBits } = modelMetrics.find(
                item => item.cumulativeBits !== 0,
              ) || { cumulativeBits: 0 };

              // cumulativeMarginDifference
              const { cumulativeMarginDifference } = modelMetrics.find(
                item => item.cumulativeMarginDifference !== 0,
              ) || { cumulativeMarginDifference: 0 };

              // cumulativeMeanAbsoluteError
              const { cumulativeMeanAbsoluteError } = modelMetrics.find(
                item => item.cumulativeMeanAbsoluteError !== 0,
              ) || { cumulativeMeanAbsoluteError: 0 };

              return (
                <Fragment>
                  <WidgetHeading>
                    Performance metrics for Tipresias
                  </WidgetHeading>
                  <WidgetSubHeading>{`Round ${roundNumber},  Season ${seasonYear} `}</WidgetSubHeading>
                  <DefinitionList items={[
                    {
                      id: 1,
                      key: 'Cumulative Correct Count',
                      value: cumulativeCorrectCount ? Math.round(cumulativeCorrectCount * 100) / 100 : '-',
                    },
                    {
                      id: 2,
                      key: 'Cumulative Bits',
                      value: Math.round(cumulativeBits * 100) / 100,
                    },
                    {
                      id: 3,
                      key: 'Cumulative Mean Absolute Error (MAE)',
                      value: Math.round(cumulativeMeanAbsoluteError * 100) / 100,
                    },
                    {
                      id: 4,
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
