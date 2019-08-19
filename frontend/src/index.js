import React from 'react';
import ReactDOM from 'react-dom';
import ApolloClient from 'apollo-boost';
import { ApolloProvider } from 'react-apollo';
import { ThemeProvider } from 'styled-components';
import App from './containers/App';
import registerServiceWorker from './registerServiceWorker';

const client = new ApolloClient({
  resolvers: {},
});

const withApollo = Component => (
  <ApolloProvider client={client}>
    <Component />
  </ApolloProvider>
);
const AppWithApollo = withApollo(App);
const theme = {
  dark: {
    backgroundColor: '#121212',
    color: '#e1e1e1',
  },
};
ReactDOM.render(<ThemeProvider theme={theme}>{AppWithApollo}</ThemeProvider>, document.getElementById('root'));
registerServiceWorker();
