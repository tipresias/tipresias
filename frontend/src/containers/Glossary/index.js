import React from 'react';
import { Route, Link } from 'react-router-dom';
// import GlossaryStyled from './style';

const Topic = ({ match }) => (
  <h3>
    Requested Param:
    {match.params.id}
  </h3>
);

const Glossary = ({ match }) => {
  console.log('match >>>', match);

  return (
    <div>
      <h2>Topics</h2>

      <ul>
        <li>
          <Link to={`${match.url}/1`}>Tip point</Link>
        </li>
        <li>
          <Link to={`${match.url}/2`}>predicted margin</Link>
        </li>
      </ul>

      <Route path={`${match.path}/:id`} component={Topic} />
      <Route
        exact
        path={match.path}
        render={() => <h3>Please select a Term.</h3>}
      />
    </div>
  );
};
// const Glossary = () => (
//   <GlossaryStyled>
//     <dl>
//       <dt>term 1</dt>
//       <dd>definition 1</dd>
//       <dt>term 2</dt>
//       <dd>definition 2</dd>
//       <dt>term 3</dt>
//       <dd>definition 3</dd>
//       <dt>term 4</dt>
//       <dd>definition 4</dd>
//     </dl>
//   </GlossaryStyled>
// );

export default Glossary;
