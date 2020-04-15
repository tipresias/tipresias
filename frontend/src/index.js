import React from 'react';
import ReactDOM from 'react-dom';
import ApolloClient from 'apollo-boost';
import { ApolloProvider } from '@apollo/react-hoc';
import { InMemoryCache } from 'apollo-cache-inmemory';
import App from './containers/App';
import registerServiceWorker from './registerServiceWorker';


// export default new ApolloClient({
//   uri: "http://localhost:8030/graphql",
//   cache: new InMemoryCache({
//       addTypename: false
//   })
// });


const client = new ApolloClient({
  cache: new InMemoryCache({
    addTypename: false,
  }),
});
// const client = new ApolloClient({});

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
