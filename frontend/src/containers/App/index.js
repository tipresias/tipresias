// @flow
import React, { Component } from 'react';
import { Query } from 'react-apollo';
import styled from 'styled-components/macro';
import GET_PREDICTIONS_QUERY from '../../graphql/getPredictions';
import createDataObject from '../../utils/CreateDataObject';
import createTableDataRows from '../../utils/CreateTableDataRows';
import PageHeader from '../../components/PageHeader';
import PageFooter from '../../components/PageFooter';
import BarChartMain from '../../components/BarChartMain';
import Select from '../../components/Select';
import Checkbox from '../../components/Checkbox';
import BarChartLoading from '../../components/BarChartLoading';
import StatusBar from '../../components/StatusBar';
// import PredictionList from '../../components/PredictionList';
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

const performanceHeaders = ['Total Points', 'Total Margin', 'MAE'];
const performanceRows = [
  ['value 1', 'value 2', 'value 3'],
];

class App extends Component<Props, State> {
  state = {
    year: 2018, // todo: add this data, according to current year, dynamic.
  };

  // todo: add this data dynamic.
  OPTIONS = [2014, 2015, 2016, 2017, 2018];

  onChangeYear = (event: SyntheticEvent<HTMLSelectElement>): void => {
    this.setState({ year: parseInt(event.currentTarget.value, 10) });
  };

  render() {
    const { year } = this.state;
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
            <Select
              name="year"
              value={year}
              onChange={this.onChangeYear}
              options={this.OPTIONS}
            />
          </WidgetFooter>
        </Widget>

        <Widget gridColumn="2 / -3">
          <Query query={GET_PREDICTIONS_QUERY} variables={{ year: 2018 }}>
            {PredictionListQueryChildren}
          </Query>
        </Widget>

        <Widget gridColumn="5 / -2">
          <Table caption="table caption" rows={performanceRows} headers={performanceHeaders} />
        </Widget>

        <PageFooter />
      </AppContainer>
    );
  }
}

export default App;
