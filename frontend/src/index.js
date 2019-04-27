import React from 'react';
import ReactDOM from 'react-dom';
import ApolloClient from "apollo-boost";
import gql from "graphql-tag";
import App from './containers/App';
import registerServiceWorker from './registerServiceWorker';

const client = new ApolloClient()

client.query({
  query: gql`{
      predictions(year: 2016) { id }
    }`
}).then(result => {
    console.log('result >>>> ',result)
  }).catch((error) => {
    console.log(error);

  });

ReactDOM.render(<App />, document.getElementById('root'));
registerServiceWorker();
