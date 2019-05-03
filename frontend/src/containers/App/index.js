// @flow
import React, { Component } from 'react';
import { Query } from 'react-apollo';
import { GET_PREDICTIONS_QUERY } from '../../graphql';
import type { Game } from '../../types';
import BarChartContainer from '../BarChartContainer';
import Select from '../../components/Select';
import Image from '../../components/Image';
import ErrorBar from '../../components/ErrorBar';
import LoadingBar from '../../components/LoadingBar';
import EmptyChart from '../../components/EmptyChart';
import BarChartSecondary from '../../components/BarChartSecondary';

type State = {
  year: number
}

type Props = {}

class App extends Component<Props, State> {
  state = {
    year: 2014
  };

  OPTIONS = [2011, 2014, 2015, 2016, 2017];

  onChangeYear = (event: SyntheticEvent<HTMLSelectElement>): void => {
    this.setState({ year: parseInt(event.currentTarget.value, 10) });
  }
  onSomethingElse = (event: SyntheticEvent<HTMLSelectElement>): void => {
    this.setState({ year: parseInt(event.currentTarget.value, 10) });
  }

  render() {
    const {
      year
    } = this.state;

    const queryChildren = ({ loading, error, data }) => {
      const nonNullData = (data || {})
      const dataWithAllPredictions = { predictions: [], ...nonNullData }
      const { predictions } = dataWithAllPredictions;

      // if loading prop is true, render loading component
      if (loading) return <LoadingBar text="Loading predictions..." />

      // if error prop is true, render error component
      if (error) return <ErrorBar text={error.message} />

      // if predictions is empty
      if (predictions.length === 0) return <EmptyChart text="No data found" />

      // if predictions prop is passed, renders barChartContainer component
      return <BarChartContainer games={predictions} />
    }

    return (
      <div className="App" style={{ backgroundColor: '#f3f3f3' }}>
        <header className="App-header">
          <Image alt="Tipresias" width={120} />
          <Select
            name="year"
            value={year}
            onChange={this.onChangeYear}
            options={this.OPTIONS}
          />
        </header>
        <Query query={GET_PREDICTIONS_QUERY} variables={{ year }} onCompleted={() => console.log("data fetched!")}>
          {queryChildren}
        </Query>
      </div>
    );
  }

}

export default App;
