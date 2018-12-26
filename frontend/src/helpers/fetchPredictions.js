// @flow
import axios from 'axios';

export default function fetchPredictions() {
  return axios.get('/predictions')
    .then(({ data: { data } }) => data);
}
