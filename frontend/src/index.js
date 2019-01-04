import React from 'react';
import ReactDOM from 'react-dom';
import App from './containers/App';
import registerServiceWorker from './registerServiceWorker';

/* global document:true */
/* eslint no-undef: "error" */

ReactDOM.render(<App />, document.getElementById('root'));
registerServiceWorker();
