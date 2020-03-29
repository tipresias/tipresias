// @flow
import React, { Component, Fragment } from 'react';
import type { Node } from 'react';
import { Query } from '@apollo/react-components';
import styled from 'styled-components/macro';
import {
  FETCH_PREDICTION_YEARS_QUERY,
  FETCH_YEARLY_PREDICTIONS_QUERY,
  FETCH_LATEST_ROUND_PREDICTIONS_QUERY,
  FETCH_LATEST_ROUND_STATS,
} from '../../graphql';
import LineChartMain from '../../components/LineChartMain';
import Select from '../../components/Select';
import BarChartLoading from '../../components/BarChartLoading';
import StatusBar from '../../components/StatusBar';
import DefinitionList from '../../components/DefinitionList';
import Table from '../../components/Table';
import ErrorBoundary from '../../components/ErrorBoundary';
import {
  WidgetStyles, WidgetHeading, WidgetFooter, DashboardContainerStyled,
} from './style';

type State = {
  year: number
};
type Props = {};

const Widget = styled.div`${WidgetStyles}`;
// TODO: CONSTANTS: this values should be prefetched from Query.
const DEFAULT_MAIN_MODEL = 'tipresias'; // add some isDefault in graphql query to know what model load as default.
const LATEST_YEAR = 2019;

class Dashboard extends Component<Props, State> {
  // make this dinamyc frmo query data
  state = {
    year: LATEST_YEAR,
  };

  onChangeYear = (event: SyntheticEvent<HTMLSelectElement>): void => {
    this.setState({ year: parseInt(event.currentTarget.value, 10) });
  };

  render() {
    const { year } = this.state;
    return (
      <ErrorBoundary>
        <DashboardContainerStyled>
          <Widget gridColumn="1 / -1">
            <WidgetHeading>
              Cumulative accuracy by round
              <Query query={FETCH_PREDICTION_YEARS_QUERY}>
                {(response: any): Node => {
                  const { loading, error, data } = response;
                  if (loading) return <p>Loading predictions...</p>;
                  if (error) return <StatusBar text={error.message} error />;
                  return (
                    <Select
                      name="year"
                      value={year}
                      onChange={this.onChangeYear}
                      options={data.fetchPredictionYears}
                    />
                  );
                }}
              </Query>
            </WidgetHeading>
            <Query query={FETCH_YEARLY_PREDICTIONS_QUERY} variables={{ year }}>
              {(response: any): Node => {
                const { loading, error, data } = response;
                if (loading) return <BarChartLoading text="Loading predictions..." />;
                if (error) return <StatusBar text={error.message} error />;
                if (data.fetchYearlyPredictions.predictionsByRound.length === 0) return <StatusBar text="No data found" empty />;
                return <LineChartMain models={data.fetchYearlyPredictions.predictionModelNames} data={data.fetchYearlyPredictions.predictionsByRound} />;
              }}
            </Query>
            <WidgetFooter>
              wip
            </WidgetFooter>
          </Widget>

          <Widget gridColumn="1 / -1">
            <WidgetHeading>Predictions</WidgetHeading>
            <Query query={FETCH_LATEST_ROUND_PREDICTIONS_QUERY} variables={{ mlModelName: DEFAULT_MAIN_MODEL }}>
              {(response: any): Node => {
                const { loading, error, data } = response;
                if (loading) return <p>Loading predictions...</p>;
                if (error) return <StatusBar text={error.message} error />;
                if (data.fetchLatestRoundPredictions.matches.length === 0) return <StatusBar text="No data found" empty />;

                const seasonYear = data.fetchLatestRoundPredictions.matches[0].year;
                const { roundNumber } = data.fetchLatestRoundPredictions;

                return (
                  <Table
                    caption={`Tipresias predictions for matches of round ${roundNumber}, season ${seasonYear}`}
                    headers={['Date', 'Predicted Winner', 'Predicted margin', 'Predicted Loser', 'is Correct?']}
                    rows={data.fetchLatestRoundPredictions.matches}
                  />
                );
              }}
            </Query>
          </Widget>

          <Widget gridColumn="1 / -2">
            <Query query={FETCH_LATEST_ROUND_STATS} variables={{ year, roundNumber: -1, mlModelName: DEFAULT_MAIN_MODEL }}>
              {(response: any): Node => {
                const { loading, error, data } = response;
                if (loading) return <p>Loading metrics...</p>;
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
  }
}

export default Dashboard;
