// @flow
import React, { Fragment, useState } from 'react';
import type { Node } from 'react';
import { Query } from '@apollo/react-components';
import styled from 'styled-components/macro';
import {
  FETCH_SEASON_METRICS_QUERY,
  FETCH_LATEST_ROUND_PREDICTIONS_QUERY,
  FETCH_LATEST_ROUND_METRICS_QUERY,
} from '../../graphql';
import type { fetchSeasonModelMetrics } from '../../graphql/graphql-types/fetchSeasonModelMetrics';
import type { fetchLatestRoundPredictions } from '../../graphql/graphql-types/fetchLatestRoundPredictions';
import type { fetchLatestRoundMetrics } from '../../graphql/graphql-types/fetchLatestRoundMetrics';
import LineChartMain from '../../components/LineChartMain';
import Select from '../../components/Select';
import Checkbox from '../../components/Checkbox';
import RadioButton from '../../components/RadioButton';
import ChartLoading from '../../components/ChartLoading';
import StatusBar from '../../components/StatusBar';
import DefinitionList from '../../components/DefinitionList';
import Table from '../../components/Table';
import Fieldset from '../../components/Fieldset';
import ErrorBoundary from '../../components/ErrorBoundary';
import {
  WidgetStyles, WidgetHeading, WidgetSubHeading, WidgetFooter, DashboardContainerStyled,
} from './style';
import dataTransformerTable from './dataTransformerTable';
import dataTransformerLineChart from './dataTransformerLineChart';

export type ModelType = {
  name: string,
  usedInCompetitions: boolean,
  isPrinciple: boolean
}

type DashboardProps = {
  metrics: Array<string>,
  models: Array<ModelType>,
  years: Array<number>
};

interface fetchSeasonModelMetricsResponse {
  loading: any;
  error: any;
  data: fetchSeasonModelMetrics;
}

interface fetchLatestRoundPredictionsResponse {
  loading: any;
  error: any;
  data: fetchLatestRoundPredictions;
}

interface fetchLatestRoundMetricsResponse {
  loading: any;
  error: any;
  data: fetchLatestRoundMetrics;
}

const Widget = styled.div`${WidgetStyles}`;

const Dashboard = ({ years, models, metrics }: DashboardProps) => {
  const latestYear = years[years.length - 1];
  const [year, setYear] = useState(latestYear);

  const initialSelectedModels = models.map(item => item.name);
  const [checkedModels, setSelectedModels] = useState(initialSelectedModels);

  const [currentMetric, setCurrentMetric] = useState(metrics[0]);
  const currentMetricLabel = currentMetric.replace(/cumulative/g, '');
  const mainWidgetTitle = `Cumulative ${currentMetricLabel} by round`;

  const onChangeModel = (event: SyntheticEvent<HTMLSelectElement>): void => {
    const checkedModel = event.currentTarget.value;
    if (checkedModels.includes(checkedModel)) {
      const updatedModels = checkedModels.filter(
        item => item !== checkedModel,
      );
      setSelectedModels(updatedModels);
    } else {
      setSelectedModels([...checkedModels, checkedModel]);
    }
  };

  const onChangeMetric = (event: SyntheticEvent<HTMLSelectElement>): void => {
    const checkedMetric = event.currentTarget.value;
    setCurrentMetric(checkedMetric);
  };

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
              FETCH_SEASON_METRICS_QUERY
            }
            variables={{
              season: year,
              forCompetitionOnly: false,
            }}
          >
            {({ loading, error, data }: fetchSeasonModelMetricsResponse): Node => {
              if (loading) return <ChartLoading text="Brrrrr ..." />;
              if (error) return <StatusBar text={error.message} error />;
              const { roundModelMetrics } = data.fetchSeasonModelMetrics;

              if (roundModelMetrics.length === 0) {
                return <StatusBar text="No data found" empty />;
              }
              const metric = { name: currentMetric, label: currentMetricLabel };
              const dataTransformed = dataTransformerLineChart(roundModelMetrics, metric);

              // @todo find a better way to add
              // unit of measure for labels that need it. ie. accuracy
              const yAxisLabel = (currentMetricLabel === 'Accuracy' ? `${currentMetricLabel} %` : currentMetricLabel);

              return (
                <LineChartMain
                  models={checkedModels}
                  data={dataTransformed}
                  xAxis={{ dataKey: 'roundNumber', label: 'Rounds' }}
                  yAxis={{ label: yAxisLabel }}
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
            <Fieldset legend="Choose a model">
              {
                initialSelectedModels.map(modelName => (
                  <Checkbox
                    id={modelName}
                    key={modelName}
                    label={modelName}
                    name={modelName}
                    value={modelName}
                    isChecked={checkedModels.includes(modelName)}
                    onChange={e => onChangeModel(e)}
                  />
                ))
              }
            </Fieldset>
            <Fieldset legend="Choose a metric">
              {
                metrics.map((metricName) => {
                  const labelName = metricName.replace(/cumulative/g, '');
                  return (
                    <RadioButton
                      key={metricName}
                      id={metricName}
                      name={metricName}
                      value={metricName}
                      label={labelName}
                      isChecked={metricName === currentMetric}
                      onChange={e => onChangeMetric(e)}
                    />
                  );
                })
              }
            </Fieldset>
          </WidgetFooter>
        </Widget>

        <Widget gridColumn="1 / -1" style={{ overflowX: 'scroll' }}>
          <WidgetHeading>Tipresias&apos;s Predictions</WidgetHeading>
          <Query query={FETCH_LATEST_ROUND_PREDICTIONS_QUERY}>
            {({ loading, error, data }: fetchLatestRoundPredictionsResponse): Node => {
              if (loading) return <p>Brrrrrr...</p>;
              if (error) return <StatusBar text={error.message} error />;
              if (data.fetchLatestRoundPredictions.matchPredictions.length === 0) {
                return (
                  <StatusBar
                    text="No data available."
                    empty
                  />
                );
              }

              const { roundNumber } = data.fetchLatestRoundPredictions;
              const { matchPredictions } = data.fetchLatestRoundPredictions;
              const rowsArray = dataTransformerTable(matchPredictions);

              if (rowsArray.length === 0) {
                return <StatusBar text="No data available." error />;
              }
              const caption = `This Table shows prediction for matches of round number ${roundNumber} of season ${latestYear}`;
              return (
                <Table
                  caption={caption}
                  headers={['Date', 'Predicted Winner', 'Predicted margin*', 'Win probability (%)*', 'Is prediction correct?']}
                  rows={rowsArray}
                />
              );
            }}
          </Query>
          <p>
            <em>
              *Margin and win probability are generated by different models
              that sometimes disagree. In those cases, the secondary prediction
              will be for a loss for the given team, resulting in negative margins
              or win probabilities less than 0.5.
            </em>
          </p>
        </Widget>

        <Widget gridColumn="1 / -2">
          <Query query={FETCH_LATEST_ROUND_METRICS_QUERY}>
            {({ loading, error, data }: fetchLatestRoundMetricsResponse): Node => {
              if (loading) return <p>Brrrrr...</p>;
              if (error) return <StatusBar text={error.message} error />;
              const {
                season,
                roundNumber,
                cumulativeBits,
                cumulativeMeanAbsoluteError,
                cumulativeCorrectCount,
                cumulativeMarginDifference,
              } = data.fetchLatestRoundMetrics;

              return (
                <Fragment>
                  <WidgetHeading>
                    Performance metrics for Tipresias
                  </WidgetHeading>
                  <WidgetSubHeading>{`Round ${roundNumber},  Season ${season} `}</WidgetSubHeading>
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
