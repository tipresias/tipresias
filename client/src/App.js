import React, { Component } from 'react';
import fetchPredictions from './lib/fetchPredictions';
import logo from './logo.svg';
import './App.css';
import BarChart from './components/BarChart';
import Select from './components/Select';

class App extends Component {
  state = {
    isLoading: true,
    yearSelected: 2011,
  };

  componentDidMount() {
    const { yearSelected } = this.state;
    fetchPredictions(yearSelected).then((data) => {
      this.setState({
        games: data,
        isLoading: false,
      });
    });
  }

  onChangeYear = (event) => {
    this.setState({ yearSelected: event.target.value });
  }

  render() {
    const {
      isLoading,
      games,
      yearSelected,
    } = this.state;

    let contentComponent;
    if (isLoading) {
      contentComponent = <div>Loading content!...</div>;
    } else {
      contentComponent = <BarChart year={yearSelected} games={games} />;
    }
    return (
      <div className="App">
        <header className="App-header">
          <img src={logo} className="App-logo" alt="logo" />
          <h1 className="App-title">Welcome to Tipresias</h1>
        </header>
        <div>
          <p className="App-intro">
            Peace among Worlds!
          </p>
          <Select
            value={yearSelected}
            onChange={this.onChangeYear}
          />
          {contentComponent}
        </div>
      </div>
    );
  }
}

export default App;
