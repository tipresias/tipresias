import React from 'react';
import ReactDOM from 'react-dom';
import ApolloClient from 'apollo-boost';
import { ApolloProvider } from 'react-apollo';
import App from './containers/App';
import registerServiceWorker from './registerServiceWorker';

const client = new ApolloClient({
  resolvers: {},
});
console.log(client);
console.log(client.cache);


const withApollo = Component => (
  <ApolloProvider client={client}>
    <Component />
  </ApolloProvider>
);
const AppWithApollo = withApollo(App);

ReactDOM.render(AppWithApollo, document.getElementById('root'));
registerServiceWorker();
