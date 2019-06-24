import React from 'react';
import { Route, Link } from 'react-router-dom';
import GlossaryStyled from './style';

const Topic = ({ match }) => (
  <div>
    <h3>
      Definition:
      {match.params.id}
    </h3>
  </div>
);

const Glossary = ({ match }) => (
  <GlossaryStyled>
    <h2>Terms used in Tipresias:</h2>
    <ul>
      <li>
        <Link to={`${match.url}/1`}>Tip Point</Link>
      </li>
      <li>
        <Link to={`${match.url}/2`}>Predicted margin</Link>
      </li>
      <li>
        <Link to={`${match.url}/3`}>Winner / Predicted winner</Link>
      </li>
      <li>
        <Link to={`${match.url}/3`}>Cumulative tip points bar chart</Link>
      </li>
    </ul>

    <Route path="/glossary/:id" component={Topic} />
  </GlossaryStyled>
);


export default Glossary;
