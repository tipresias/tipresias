import React, { Component } from 'react';
import axios from 'axios';
import logo from './logo.svg';
import './App.css';
import BarChart from './components/BarChart';

class App extends Component {
  state = { 
    isLoading: true,
    year: 2011,
    years: [2011, 2012, 2013, 2014]
  };

  componentDidMount() {
    axios.get(`/predictions`)
      .then( response => {
        this.setState({ 
          games: response.data.data,
          isLoading: false,
        });
      });
  }
  
  updateYear = (event) => {
    this.setState({year: event.target.value})
  }

  render() {
    const isLoading = this.state.isLoading;
    let contentComponent;
    if (isLoading) {
      contentComponent = <div>Loading content!...</div>;
    } else {
      contentComponent = <BarChart data = { this.state.games } />
    }
    return (
      <div className="App">
        <header className="App-header">
          <img src={logo} className="App-logo" alt="logo" />
          <h1 className="App-title">Welcome to Tipresias</h1>
        </header>
        <div>
        <p className="App-intro">
          Peace among worlds!
        </p>
        <select value = { this.state.year } name = "year" onChange = { this.updateYear }>
          { 
            this.state.years.map(item => (
            <option key = { item } value = { item }>
              { item }
            </option>)
            )
          }
        </select>
        { contentComponent }         
        </div>
      </div>
    );
  }
}

export default App;
