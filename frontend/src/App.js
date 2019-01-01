// @flow
import React, { Component } from 'react';
import type { Game } from './types';
import fetchPredictions from './services/predictions/fetch';
import filterDataByYear from './helpers/filterGameByYear';
import logo from './logo.svg';
import './App.css';
import BarChartContainer from './components/BarChartContainer';
import Select from './components/Select';

type State = {
  isLoading: boolean,
  year: number,
  allGames: Array<Game>,
  gamesByYear: Array<Game>
}

type Props = {}

class App extends Component<Props, State> {
  state = {
    isLoading: true,
    year: 2011,
    allGames: [],
    gamesByYear: [],
  };

  componentDidMount() {
    fetchPredictions().then((data) => {
      this.setState({ allGames: data }, () => {
        const { allGames, year } = this.state;
        this.setGamesByYear(allGames, year);
      });
    }).catch((err) => {
      console.log(err);
    });
  }

  componentDidUpdate(prevProps: Props, prevState: State) {
    const { allGames, year } = this.state;
    if (year !== prevState.year) {
      this.setGamesByYear(allGames, year);
    }
  }

  onChangeYear = (event: SyntheticEvent<HTMLSelectElement>): void => {
    this.setState({ year: parseInt(event.currentTarget.value, 10) });
  }

  setGamesByYear(allGames: Array<Game>, year: number) {
    const gamesByYear = filterDataByYear(allGames, year);
    this.setState({
      gamesByYear,
      isLoading: false,
    });
  }

  render() {
    const {
      isLoading,
      gamesByYear,
      year,
    } = this.state;

    let contentComponent;
    if (isLoading) {
      contentComponent = <div>Loading content!...</div>;
    } else {
      contentComponent = <BarChartContainer year={year} gamesByYear={gamesByYear} />;
    }
    return (
      <div className="App">
        <header className="App-header">
          <img src={logo} className="App-logo" alt="logo" />
          <Select
            value={year}
            onChange={this.onChangeYear}
            options={[2011, 2012, 2013, 2014]}
          />
        </header>
        <div className="App-content">
          {contentComponent}
        </div>
      </div>
    );
  }
}

export default App;
