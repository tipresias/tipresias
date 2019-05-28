// @flow
import React from 'react';
import type { Node } from 'react';
import styled from 'styled-components/macro';

import { List, ListItem, StatStyles } from './style';

type Props = {
  items: Array<Object>
}

const Stat = styled.div`${StatStyles}`;

const renderTeamWinner = team => (
  <Stat key={team.name} isHighlighted>
    <div className="key">
      {team.name}
    </div>
    <div className="value">{team.predictedMargin}</div>
  </Stat>
);

const renderTeam = team => (
  <Stat key={team.name}>
    <div className="key">
      {team.name}
    </div>
  </Stat>
);

const PredictionList = ({ items }: Props): Node => {
  if (!items || items.length === 0) { return (<p>no data found</p>); }
  return (
    <List>
      <ListItem>
        <Stat>Away</Stat>
        <Stat>Home</Stat>
      </ListItem>
      {
        items && items.length > 0 && items.map(item => (
          <ListItem key={item.match}>
            {
              item.teams.map(
                team => (team.predictedMargin !== null ? renderTeamWinner(team) : renderTeam(team)),
              )
            }
          </ListItem>
        ))
      }
    </List>
  );
};

export default PredictionList;
