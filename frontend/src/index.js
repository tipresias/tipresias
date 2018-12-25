import React from 'react';
import ReactDOM from 'react-dom';
import './index.css';
import App from './App';
import registerServiceWorker from './registerServiceWorker';

/* global document:true */
/* eslint no-undef: "error" */

ReactDOM.render(<App />, document.getElementById('root'));
registerServiceWorker();
