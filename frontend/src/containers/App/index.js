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

const Widget = styled.div`
  background-color: #fff;
  border: 1px solid rgba(0,0,0,.125);
  border-radius: .25rem;
  box-shadow: 0 0.25rem 0.75rem rgba(0, 0, 0, .05);
  padding: 1.25rem;
`;

const WidgetHeading = styled.h3`
  font-style: bold;
  font-size: 18px;
  color: #373A3C;
  letter-spacing: 0;
  text-align: left;
`;

const List = styled.div`
  display: flex;
  flex-direction:column;
`;

const ListItem = styled.div`
  display: flex;
  background: #FFFFFF;
  border: 1px solid #DDDDDD;
  border-radius: 4px;
`;

const Stat = styled.div`
  display: flex;
  align-items: center;

  .key {
    font-size: 16px;
    color: #373A3C;
  }
  .value {
    font-size: 26px;
    color: #373A3C;
  }
`;

const WidgetFooter = styled.div`
  padding: 1rem 0.5rem;
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
        </HeaderStyled>
        <Widget>
          <WidgetHeading>Tipresias's predictions for round x</WidgetHeading>
          <List>
            <ListItem>
              <Stat>
                <div className="key">Team Name 1</div>
                <div className="value">77</div>
              </Stat>
              <Stat>
                <div className="key">Team Name 2</div>
                <div className="value">90</div>
              </Stat>
            </ListItem>
          </List>

        </Widget>

        <Widget>
          <WidgetHeading>Model performace round x</WidgetHeading>
          <List>
            <ListItem>
              <Stat>
                <div className="key">Total Points</div>
                <div className="value">90</div>
              </Stat>
            </ListItem>
            <ListItem>
              <Stat>
                <div className="key">Total Margin</div>
                <div className="value">77</div>
              </Stat>
            </ListItem>
            <ListItem>
              <Stat>
                <div className="key">MAE</div>
                <div className="value">77</div>
              </Stat>
            </ListItem>
            <ListItem>
              <Stat>
                <div className="key">Bits</div>
                <div className="value">49</div>
              </Stat>
            </ListItem>
          </List>
        </Widget>

        <Widget>
          <WidgetHeading>Cumulative points per round:</WidgetHeading>
          <Query query={GET_PREDICTIONS_QUERY} variables={{ year }}>
            {queryChildren}
          </Query>
          <WidgetFooter>
            <input type="checkbox" id="tipresias" name="model" value="tipresias" />
            <label htmlFor="tipresias">tipresias</label>

            <input type="checkbox" id="another" name="model" value="another" />
            <label htmlFor="another">another</label>
            <Select
              name="year"
              value={year}
              onChange={this.onChangeYear}
              options={this.OPTIONS}
            />
          </WidgetFooter>
        </Widget>
      </AppContainerStyled>
    );
  }
}

export default App;
