import React from 'react';
import ReactDOM from 'react-dom';
import ApolloClient from 'apollo-boost';
import { ApolloProvider } from '@apollo/react-hoc';
import App from './containers/App';
import registerServiceWorker from './registerServiceWorker';

const client = new ApolloClient({
  resolvers: {},
});

// const withApollo = Component => (
//   <ApolloProvider client={client}>
//     <Component />
//   </ApolloProvider>
// );
// const AppWithApollo = withApollo(App);


ReactDOM.render(
  <ApolloProvider client={client}>
    <App />
  </ApolloProvider>,

  document.getElementById('root'),
);
registerServiceWorker();
