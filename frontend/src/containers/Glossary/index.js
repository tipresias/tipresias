import React from 'react';
import { Route, Link } from 'react-router-dom';
import GlossaryStyled from './style';

const Topic = ({ match }) => (
  <div>
    <h3>
      Topic:
      {match.params.id}
    </h3>
  </div>
);

const Glossary = ({ match }) => (
  <GlossaryStyled>
    <h2>Topics</h2>
    <ul>
      <li>
        <Link to={`${match.url}/1`}>Tip point</Link>
      </li>
      <li>
        <Link to={`${match.url}/2`}>another term</Link>
      </li>
      <li>
        <Link to={`${match.url}/3`}>another term</Link>
      </li>
    </ul>

    <Route path="/glossary/:id" component={Topic} />
  </GlossaryStyled>
);


export default Glossary;
