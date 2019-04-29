// @flow
import React, { Fragment, Component } from 'react';
import { Query } from 'react-apollo';
import { getPredictionsQuery } from '../../graphql';
import type { Game } from '../../types';
// import fetchPredictions from '../../services/fetchPredictions';
// import filterDataByYear from '../../utils/filterGameByYear';
import logo from './tipresias-logo.svg';
import './App.css';
// import BarChartContainer from '../BarChartContainer';
import Select from '../../components/Select';
import BarChartSecondary from '../../components/BarChartSecondary';

type State = {
  year: number
}

type Props = {
}

class App extends Component<Props, State> {
  state = {
    year: 2014
  };

  // componentDidMount() {
  // fetchPredictions('/predictions').then((data) => {
  //   this.setState({ allGames: data }, () => {
  //     const { allGames, year } = this.state;
  //     // this.setGamesByYear(allGames, year);
  //   });
  // }).catch((err) => {
  //   console.log(err);
  // });
  // }

  // componentDidUpdate(prevProps: Props, prevState: State) {
  // const { allGames, year } = this.state;
  // if (year !== prevState.year) {
  //   this.setGamesByYear(allGames, year);
  // }
  // }

  onChangeYear = (event: SyntheticEvent<HTMLSelectElement>): void => {
    this.setState({ year: parseInt(event.currentTarget.value, 10) });
  }

  // setGamesByYear(allGames: Array<Game>, year: number) {
  //   const gamesByYear = filterDataByYear(allGames, year);
  //   this.setState({
  //     gamesByYear,
  //     isLoading: false,
  //   });
  // }

  render() {
    const {
      year
    } = this.state;


    // let contentComponent;
    // if (isLoading) {
    //   contentComponent = <div>Loading content!...</div>;
    // } else {
    //   contentComponent = <BarChartContainer year={year} gamesByYear={games} />;
    // }
    const queryChildren = ({ loading, error, data }) => {
      if (loading) return <div>loading...</div>
      if (error) return <div>error...</div>
      return <BarChartSecondary games={data} />
    }

    return (
      <div className="App">
        <header className="App-header">
          <img src={logo} className="App-logo" alt="logo" />
          <Select
            value={year}
            onChange={this.onChangeYear}
            options={[2011, 2012, 2013, 2014, 2015, 2016, 2017]}
          />
        </header>
        <Query query={getPredictionsQuery} variables={{ year }}>
          {queryChildren}
        </Query>
      </div>
    );
  }

}

export default App;
