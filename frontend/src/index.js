import React from 'react';
import ReactDOM from 'react-dom';
import ApolloClient from 'apollo-boost';
import { ApolloProvider, withApollo } from 'react-apollo';
import { defaults, resolvers } from './graphql/resolvers';
import { typeDefs } from './graphql/schema';
import App from './containers/App';
import registerServiceWorker from './registerServiceWorker';

console.log(typeDefs);

const client = new ApolloClient({
  clientState: {
    defaults,
    resolvers,
    typeDefs,
  },
});

const AppWithClient = withApollo(App);

ReactDOM.render(
  <ApolloProvider client={client}>
    <AppWithClient />
  </ApolloProvider>,
  document.getElementById('root'),
);

registerServiceWorker();
