// @flow
import React, { Component } from 'react';
import styled from 'styled-components';
import { Query } from 'react-apollo';
import GET_PREDICTIONS_QUERY from '../../graphql/getPredictions';
// import type { Game } from '../../types';
import images from '../../images';
import BarChartMain from '../../components/BarChartMain';
import BarChartContainer from '../BarChartContainer';
import Select from '../../components/Select';
import ErrorBar from '../../components/ErrorBar';
import LoadingBar from '../../components/LoadingBar';
import EmptyChart from '../../components/EmptyChart';

const tipresiasLogo = images.logo;

type State = {
  year: number
};

type Props = {};

const AppContainerStyled = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  grid-gap: 5px;
  font-family: sans-serif;
  @media (min-width: 768px) {
    grid-template-columns: 1fr 18% 18% 18% 18% 1fr;
    grid-template-rows: 80px auto auto 100px;
    grid-gap: 20px;
  }
`;

const HeaderStyled = styled.header`
  grid-column: 1 / -1;
  display:flex;
  position relative;
  align-items: center;
  justify-content: center;
  background-color: white;
  border-bottom: 1px solid rgba(0,0,0,.125);
  @media (min-width: 768px) {
    grid-column: 2 / -2;
  }
`;

const LogoStyled = styled.img`
  height: auto;
  width: 150px;
`;

const HeaderLinksStyled = styled.div`
  position: absolute;
  right: 0;
  a {
    font-size: 1rem;
    color: rgba(0, 0, 0, 0.3);
    padding: 0.5rem;
  }
`;

const Widget = styled.div`
  grid-column: 1/ -1;
  background-color: #fff;
  border: 1px solid rgba(0, 0, 0, 0.125);
  border-radius: 0.25rem;
  box-shadow: 0 0.25rem 0.75rem rgba(0, 0, 0, 0.05);
  padding: 1.25rem;
  @media (min-width: 768px) {
    grid-column: ${props => props.gridColumn};
  }
`;

const WidgetHeading = styled.h3`
  font-style: bold;
  font-size: 0.8rem;
  color: #373a3c;
  letter-spacing: 0;
  text-align: left;
`;

const List = styled.div`
  display: flex;
  flex-direction: column;
`;

const ListItem = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  border: 1px solid #dddddd;
  border-radius: 4px;
`;

const Stat = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex: 1;
  padding: 0.5rem;
  &::after {
    content: "|";
    float: right;
    color: rgba(0, 0, 0, 0.125);
  }
  &:last-child::after {
    display: none;
  }
  .key {
    font-size: 1rem;
    color: #373a3c;
  }
  .value {
    font-size: 1.625rem;
    color: #373a3c;
  }
`;

const WidgetFooter = styled.div`
  padding: 1rem 0.5rem;
`;

const FooterStyled = styled.footer`
  grid-column: 1 / -1;
  background: #f0f3f7;
  border-top: 1px solid #d7d7d7;
  text-align: center;
  font-size: 1rem;
  color: #373a3c;
  a {
    color: #373a3c;
  }
`;

class App extends Component<Props, State> {
  state = {
    year: 2014,
  };

  OPTIONS = [2011, 2014, 2015, 2016, 2017];

  onChangeYear = (event: SyntheticEvent<HTMLSelectElement>): void => {
    this.setState({ year: parseInt(event.currentTarget.value, 10) });
  };

  onSomethingElse = (event: SyntheticEvent<HTMLSelectElement>): void => {
    this.setState({ year: parseInt(event.currentTarget.value, 10) });
  };

  render() {
    const { year } = this.state;

    // const BarChartCustomQueryChildren = ({ loading, error, data }) => {
    //   const nonNullData = data || {};
    //   const dataWithAllPredictions = { predictions: [], ...nonNullData };
    //   const { predictions } = dataWithAllPredictions;

    //   if (loading) return <LoadingBar text="Loading predictions..." />;

    //   if (error) return <ErrorBar text={error.message} />;

    //   if (predictions.length === 0) return <EmptyChart text="No data found" />;

    //   return <BarChartContainer games={predictions} />;
    // };

    const BarChartMainQueryChildren = ({ loading, error, data }) => {
      const nonNullData = data || {};
      const dataWithAllPredictions = { predictions: [], ...nonNullData };
      const { predictions } = dataWithAllPredictions;

      if (loading) return <LoadingBar text="Loading predictions..." />;

      if (error) return <ErrorBar text={error.message} />;

      if (predictions.length === 0) return <EmptyChart text="No data found" />;

      return <BarChartMain data={predictions} />;
    };

    return (
      <AppContainerStyled>
        <HeaderStyled>
          <LogoStyled src={tipresiasLogo} alt="Tipresias" width="120" />
          <HeaderLinksStyled>
            <a href="https://github.com/tipresias">About</a>
          </HeaderLinksStyled>
        </HeaderStyled>


        <Widget gridColumn="2 / -2">
          <Query query={GET_PREDICTIONS_QUERY} variables={{ year }}>
            {BarChartMainQueryChildren}
          </Query>
        </Widget>

        {/* <Widget gridColumn="2 / -2">
          <WidgetHeading>Cumulative points per round:</WidgetHeading>
          <Query query={GET_PREDICTIONS_QUERY} variables={{ year }}>
            {BarChartCustomQueryChildren}
          </Query>
          <WidgetFooter>
            <label htmlFor="tipresias">
              tipresias
              <input
                type="checkbox"
                id="tipresias"
                name="model"
                value="tipresias"
              />
            </label>
            <label htmlFor="another">
              another
              <input type="checkbox" id="another" name="model" value="another" />
            </label>
            <Select
              name="year"
              value={year}
              onChange={this.onChangeYear}
              options={this.OPTIONS}
            />
          </WidgetFooter>
        </Widget> */}

        <Widget gridColumn="2 / 4">
          <WidgetHeading>Tipresias predictions for round x</WidgetHeading>
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

        <Widget gridColumn="4 / -2">
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

        <FooterStyled>
          <p>
            Tipresias 2019 - Created in Melbourne by
            <a href="https://github.com/tipresias">Team Tipresias</a>
          </p>
          <p>
            <a href="#top">back to top</a>
          </p>
        </FooterStyled>
      </AppContainerStyled>
    );
  }
}

export default App;
