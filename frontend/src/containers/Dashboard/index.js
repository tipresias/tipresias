// @flow
import React, { Component, Fragment } from 'react';
import type { Node } from 'react';
import { Query } from 'react-apollo';
import styled from 'styled-components/macro';
import {
  FETCH_PREDICTION_YEARS_QUERY,
  FETCH_YEARLY_PREDICTIONS_QUERY,
  FETCH_LATEST_ROUND_PREDICTIONS_QUERY,
  FETCH_LATEST_ROUND_STATS,
} from '../../graphql';
import BarChartMain from '../../components/BarChartMain';
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

class Dashboard extends Component<Props, State> {
  state = {
    year: 2019,
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
            <WidgetHeading>Cumulative points per round</WidgetHeading>
            <Query query={FETCH_YEARLY_PREDICTIONS_QUERY} variables={{ year }}>
              {(response: any): Node => {
                const { loading, error, data } = response;
                if (loading) return <BarChartLoading text="Loading predictions..." />;
                if (error) return <StatusBar text={error.message} error />;
                if (data.fetchYearlyPredictions.predictionsByRound.length === 0) return <StatusBar text="No data found" empty />;
                return <BarChartMain data={data.fetchYearlyPredictions.predictionsByRound} />;
              }}
            </Query>
            <WidgetFooter>
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
            </WidgetFooter>
          </Widget>

          <Widget gridColumn="1 / -1">
            <Query query={FETCH_LATEST_ROUND_PREDICTIONS_QUERY}>
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
            <Query query={FETCH_LATEST_ROUND_STATS}>
              {(response: any): Node => {
                const { loading, error, data } = response;
                if (loading) return <p>Loading metrics...</p>;
                if (error) return <StatusBar text={error.message} error />;
                const { seasonYear, roundNumber, modelStats } = data.fetchLatestRoundStats;
                return (
                  <Fragment>
                    <WidgetHeading>
                      {`${modelStats.modelName} performance metrics for round ${roundNumber} season ${seasonYear}`}

                    </WidgetHeading>
                    <DefinitionList items={[
                      {
                        id: 1,
                        key: 'Cumulative Correct Count',
                        value: modelStats.cumulativeCorrectCount,
                      },
                      {
                        id: 2,
                        key: 'Cumulative Mean Absolute Error (MAE)',
                        value: modelStats.cumulativeMeanAbsoluteError,
                      },
                      {
                        id: 1,
                        key: 'Cumulative Margin Difference',
                        value: modelStats.cumulativeMarginDifference,
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
