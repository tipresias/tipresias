// @flow
import React, { Component } from 'react';
import { Query } from 'react-apollo';
import styled from 'styled-components/macro';
import GET_PREDICTIONS_QUERY from '../../graphql/getPredictions';
import createDataObject from '../../utils/CreateDataObject';
import PageHeader from '../../components/PageHeader';
import PageFooter from '../../components/PageFooter';
import BarChartMain from '../../components/BarChartMain';
import Select from '../../components/Select';
import Checkbox from '../../components/Checkbox';
import BarChartLoading from '../../components/BarChartLoading';
import StatusBar from '../../components/StatusBar';
import PredictionList from '../../components/PredictionList';
import {
  AppContainer, WidgetStyles, WidgetHeading, WidgetFooter,
} from './style';

type State = {
  year: number
};

const itemsMocked = [
  {
    match: 1,
    teams: [
      {
        name: 'team ABC', isHome: true, predictedMargin: 35,
      },
      {
        name: 'team DEF', isHome: false, predictedMargin: null,
      }],
  },
  {
    match: 2,
    teams: [
      {
        name: 'team GHI', isHome: false, predictedMargin: null,
      },
      {
        name: 'team JKL', isHome: true, predictedMargin: 10,
      }],
  },
  {
    match: 3,
    teams: [
      {
        name: 'team MNL', isHome: false, predictedMargin: 50,
      },
      {
        name: 'team OPQ', isHome: true, predictedMargin: null,
      }],
  },
  {
    match: 4,
    teams: [
      {
        name: 'team RST', isHome: true, predictedMargin: null,
      },
      {
        name: 'team UVW', isHome: false, predictedMargin: 12,
      }],
  },
];

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

class App extends Component<Props, State> {
  state = {
    year: 2014,
  };

  OPTIONS = [2011, 2014, 2015, 2016, 2017, 2018];

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

        <Widget gridColumn="2 / 4">
          <WidgetHeading>Tipresias predictions for current round in season</WidgetHeading>
          <PredictionList items={itemsMocked} />
        </Widget>

        <Widget gridColumn="4 / -2">
          <WidgetHeading>Model performace round x</WidgetHeading>
          <p>wip</p>
        </Widget>

        <PageFooter />
      </AppContainer>
    );
  }
}

export default App;
