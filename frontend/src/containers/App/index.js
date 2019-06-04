// @flow
import React, { Component } from 'react';
import { Query } from 'react-apollo';
import styled from 'styled-components/macro';
import { GET_PREDICTIONS_QUERY, GET_PREDICTION_YEARS_QUERY } from '../../graphql';
import createDataObject from '../../utils/CreateDataObject';
import createTableDataRows from '../../utils/CreateTableDataRows';
import PageHeader from '../../components/PageHeader';
import PageFooter from '../../components/PageFooter';
import BarChartMain from '../../components/BarChartMain';
import Select from '../../components/Select';
import Checkbox from '../../components/Checkbox';
import BarChartLoading from '../../components/BarChartLoading';
import StatusBar from '../../components/StatusBar';
import DefinitionList from '../../components/DefinitionList';
import Table from '../../components/Table';
import {
  AppContainer, WidgetStyles, WidgetHeading, WidgetFooter,
} from './style';

type State = {
  year: number
};

type Props = {};

const Widget = styled.div`${WidgetStyles}`;

const BarChartMainQueryChildren = ({ loading, error, data }) => {
  const nonNullData = data || {};
  const dataWithAllPredictions = { predictions: [], ...nonNullData };
  const { predictions } = dataWithAllPredictions;

  if (loading) return <BarChartLoading text="Loading predictions..." />;
  if (error) return <StatusBar text={error.message} error />;
  if (predictions.length === 0) return <StatusBar text="No data found" empty />;

  const dataObject = createDataObject(predictions);

  return <BarChartMain data={dataObject} />;
};

const PredictionListQueryChildren = ({ loading, error, data }) => {
  const nonNullData = data || {};
  const dataWithAllPredictions = { predictions: [], ...nonNullData };
  const { predictions } = dataWithAllPredictions;

  if (loading) return <p>Loading predictions...</p>;
  if (error) return <StatusBar text={error.message} error />;
  if (predictions.length === 0) return <StatusBar text="No data found" empty />;

  const rows = createTableDataRows(predictions);
  return (
    <Table
      caption="Tipresias predictions for matches of round X, season 2019"
      headers={['Date', 'Winner', 'Predicted margin', 'Loser']}
      rows={rows}
    />
  );
};


class App extends Component<Props, State> {
  state = {
    year: 2018, // todo: add this data, according to current year, dynamic.
  };

  PERFORMANCE_ITEMS = [
    {
      id: 1,
      key: 'Total Points',
      value: 'wip',
    },
    {
      id: 2,
      key: 'Total Margin',
      value: 'wip',
    },
    {
      id: 3,
      key: 'MAE',
      value: 'wip',
    },
  ];

  onChangeYear = (event: SyntheticEvent<HTMLSelectElement>): void => {
    this.setState({ year: parseInt(event.currentTarget.value, 10) });
  };

  render() {
    const { year } = this.state;

    const PredictionYearsQueryChildren = ({ loading, error, data }) => {
      if (loading) return <p>Loading predictions...</p>;
      if (error) return <StatusBar text={error.message} error />;
      return (
        <Select
          name="year"
          value={year}
          onChange={this.onChangeYear}
          options={data.predictionYears}
        />
      );
    };


    return (
      <AppContainer>
        <PageHeader />
        <Widget gridColumn="2 / -2">
          <WidgetHeading>Cumulative points per round</WidgetHeading>
          <Query query={GET_PREDICTIONS_QUERY} variables={{ year }}>
            {BarChartMainQueryChildren}
          </Query>
          <WidgetFooter>
            <Checkbox
              label="Tipresias"
              id="tipresias"
              name="model"
              value="tipresias"
              onChange={() => {
                console.log('onChange tipresias');
              }}
            />
            <Checkbox
              label="Benchmark estimator"
              id="benchmark_estimator"
              name="model"
              value="benchmark_estimator"
              onChange={() => {
                console.log('onChange benchmark_estimator');
              }}
            />

            <Query query={GET_PREDICTION_YEARS_QUERY}>
              {PredictionYearsQueryChildren}
            </Query>

          </WidgetFooter>
        </Widget>

        <Widget gridColumn="2 / -2">
          <Query query={GET_PREDICTIONS_QUERY} variables={{ year: 2018 }}>
            {PredictionListQueryChildren}
          </Query>
        </Widget>

        <Widget gridColumn="2 / -4">
          <WidgetHeading>Tipresias performace round X, season 2019</WidgetHeading>
          <DefinitionList items={this.PERFORMANCE_ITEMS} />
        </Widget>

        <PageFooter />
      </AppContainer>
    );
  }
}

export default App;
