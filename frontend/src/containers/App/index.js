// @flow
import React, { Component } from 'react';
import styled from 'styled-components';
import { Query } from 'react-apollo';
import GET_PREDICTIONS_QUERY from '../../graphql/getPredictions';
// import type { Game } from '../../types';
import images from '../../images';
import BarChartContainer from '../BarChartContainer';
import Select from '../../components/Select';
import ErrorBar from '../../components/ErrorBar';
import LoadingBar from '../../components/LoadingBar';
import EmptyChart from '../../components/EmptyChart';

const tipresiasLogo = images.logo;

type State = {
  year: number
}

type Props = {}

const AppContainerStyled = styled.div`
  font-family: sans-serif;
  text-align: center;
  background-color: #f3f3f3;
`;

const LogoStyled = styled.img`
  height: auto;
  width: 15%
`;

const HeaderStyled = styled.header`
  background-color: white;
  padding: 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

class App extends Component<Props, State> {
  state = {
    year: 2014,
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
      year,
    } = this.state;

    const queryChildren = ({ loading, error, data }) => {
      const nonNullData = (data || {});
      const dataWithAllPredictions = { predictions: [], ...nonNullData };
      const { predictions } = dataWithAllPredictions;

      if (loading) return <LoadingBar text="Loading predictions..." />;

      if (error) return <ErrorBar text={error.message} />;

      if (predictions.length === 0) return <EmptyChart text="No data found" />;

      return <BarChartContainer games={predictions} />;
    };

    return (
      <AppContainerStyled>
        <HeaderStyled>
          <LogoStyled src={tipresiasLogo} alt="Tipresias" width="120" />
          <Select
            name="year"
            value={year}
            onChange={this.onChangeYear}
            options={this.OPTIONS}
          />
        </HeaderStyled>
        <Query query={GET_PREDICTIONS_QUERY} variables={{ year }}>
          {queryChildren}
        </Query>
      </AppContainerStyled>
    );
  }
}

export default App;
