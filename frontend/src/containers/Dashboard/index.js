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
import BarChartLoading from '../../components/BarChartLoading';
import StatusBar from '../../components/StatusBar';
import DefinitionList from '../../components/DefinitionList';
// import Table from '../../components/Table';
import ErrorBoundary from '../../components/ErrorBoundary';
import {
  WidgetStyles, WidgetHeading, WidgetFooter, DashboardContainerStyled,
} from './style';
import { dataTransformer } from './dataTransformer';

type DashboardProps = {
  defaultModel: string,
  years: Array<number>;
};

const Widget = styled.div`${WidgetStyles}`;
// TODO: CONSTANTS: this values should be prefetched from Query.
// const defaultModel = 'tipresias'; // add some isDefault in graphql query to know what model load as default.

const Dashboard = ({ defaultModel, years }: DashboardProps) => {
  const latestYear = years[years.length - 1];
  const [year, setYear] = useState(latestYear);

  return (
    <ErrorBoundary>
      <DashboardContainerStyled>
        <Widget gridColumn="1 / -1">
          <WidgetHeading>
              Cumulative accuracy by round
            <Select
              name="year"
              value={year}
              onChange={(event: SyntheticEvent<HTMLSelectElement>): void => {
                setYear(parseInt(event.currentTarget.value, 10));
              }}
              options={years}
            />
          </WidgetHeading>
          <Query query={FETCH_YEARLY_PREDICTIONS_QUERY} variables={{ year }}>
            {(response: any): Node => {
              const { loading, error, data } = response;
              if (loading) return <BarChartLoading text="Brrrrr ..." />;
              if (error) return <StatusBar text={error.message} error />;
              if (data.fetchYearlyPredictions.predictionsByRound.length === 0) return <StatusBar text="No data found" empty />;
              return <LineChartMain models={data.fetchYearlyPredictions.predictionModelNames} data={data.fetchYearlyPredictions.predictionsByRound} />;
            }}
          </Query>
          <WidgetFooter>
              ...models check boxes goes here...
          </WidgetFooter>
        </Widget>

        <Widget gridColumn="1 / -1">
          <WidgetHeading>Predictions</WidgetHeading>
          <Query query={FETCH_LATEST_ROUND_PREDICTIONS_QUERY}>
            {(response: any): Node => {
              const { loading, error, data } = response;
              if (loading) return <p>Brrrrrr...</p>;
              if (error) return <StatusBar text={error.message} error />;
              if (data.fetchLatestRoundPredictions.matches.length === 0) return <StatusBar text="No data found" empty />;

              // const seasonYear = data.fetchLatestRoundPredictions.matches[0].year;
              // const { roundNumber } = data.fetchLatestRoundPredictions;

              const rowsArray = dataTransformer(data.fetchLatestRoundPredictions.matches);
              console.log('rowsArray >>>', rowsArray);

              // if (rowsArray.length === 0) {
              //   return <StatusBar text="No data available." error />;
              // }

              // <Table
              //   caption={`Tipresias predictions for matches of round ${roundNumber}, season ${seasonYear}`}
              //   headers={['Date', 'Predicted Winner', 'Predicted margin', 'Predicted Loser', 'is Correct?']}
              //   rows={rowsArray}
              // />
              return (
                <div>wip</div>
              );
            }}
          </Query>
        </Widget>

        <Widget gridColumn="1 / -2">
          <Query query={FETCH_LATEST_ROUND_STATS} variables={{ year, roundNumber: -1, mlModelName: defaultModel }}>
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
                    {`${modelName} performance metrics for round ${roundNumber} season ${seasonYear}`}

                  </WidgetHeading>
                  <DefinitionList items={[
                    {
                      id: 1,
                      key: 'Cumulative Correct Count',
                      value: cumulativeCorrectCount,
                    },
                    {
                      id: 2,
                      key: 'Cumulative Mean Absolute Error (MAE)',
                      value: cumulativeMeanAbsoluteError,
                    },
                    {
                      id: 3,
                      key: 'Cumulative Margin Difference',
                      value: cumulativeMarginDifference,
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
