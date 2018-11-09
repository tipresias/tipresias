import React, { Component } from 'react';
import fetchPredictions from './helpers/fetchPredictions';
import filterDataByYear from './helpers/filterDataByYear';
import logo from './logo.svg';
import './App.css';
import BarChartContainer from './components/BarChartContainer';
import Select from './components/Select';

class App extends Component {
  state = {
    isLoading: true,
    year: 2011,
    allGames: [],
  };

  componentDidMount() {
    fetchPredictions().then((data) => {
      this.setState({ allGames: data }, () => {
        const { allGames, year } = this.state;
        this.setGamesByYear(allGames, year);
      });
    });
  }

  componentDidUpdate(prevProps, prevState) {
    const { allGames, year } = this.state;
    if (year !== prevState.year) {
      this.setGamesByYear(allGames, year);
    }
  }

  onChangeYear = (event) => {
    this.setState({ year: event.target.value });
  }

  setGamesByYear(allGames, year) {
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
          <h1 className="App-title">Welcome to Tipresias</h1>
        </header>
        <div>
          <p className="App-intro">
            <Select
              value={year}
              onChange={this.onChangeYear}
            />
          </p>

          {contentComponent}
        </div>
      </div>
    );
  }
}

export default App;
