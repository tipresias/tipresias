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

// grid 3 cols and 3 rows
const AppContainerStyled = styled.div`
  display: grid;
  grid-template-columns: 1fr 18% 18% 18% 18% 1fr;
  grid-template-rows: 80px auto auto 100px;
  grid-gap: 20px;
  font-family: sans-serif;
`;

const HeaderStyled = styled.header`
  grid-column: 2 / -2;
  display:flex;
  position relative;
  align-items: center;
  justify-content: center;
  background-color: white;
  border-bottom: 1px solid rgba(0,0,0,.125);
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
    color: rgba(0,0,0,0.30);
    padding: 0.5rem;
  }
`;

const Widget = styled.div`
  grid-column: ${props => props.gridColumn};
  background-color: #fff;
  border: 1px solid rgba(0,0,0,.125);
  border-radius: .25rem;
  box-shadow: 0 0.25rem 0.75rem rgba(0, 0, 0, .05);
  padding: 1.25rem;
`;

const WidgetHeading = styled.h3`
  font-style: bold;
  font-size: 0.8rem;
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
  justify-content: center;
  align-items: center;
  border: 1px solid #DDDDDD;
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
    color: rgba(0,0,0,.125);
  }
  &:last-child::after {
    display:none;
  }
  .key {
    font-size: 1rem;
    color: #373A3C;
  }
  .value {
    font-size: 1.625rem;
    color: #373A3C;
  }
`;

const WidgetFooter = styled.div`
  padding: 1rem 0.5rem;
`;

const FooterStyled = styled.footer`
  grid-column: 1 / -1;
  background: #F0F3F7;
  border-top: 1px solid #D7D7D7;
  text-align: center;
  font-size: 1rem;
  color: #373A3C;
  a {
    color: #373A3C;
  }
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
          <HeaderLinksStyled>
            <a href="#">About</a>
          </HeaderLinksStyled>
        </HeaderStyled>


        <Widget gridColumn="2 / -2">
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

        <Widget gridColumn="2 / 4">
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
          <p>Tipresias 2019 - Created in Melbourne by <a href="https://github.com/tipresias">Team Tipresias</a></p>
          <p>
            <a href="#top">back to top</a>
          </p>
        </FooterStyled>
      </AppContainerStyled>
    );
  }
}

export default App;
