// @flow
import axios from 'axios';

export default function fetchPredictions(endpoint: string) {
  return axios({
    method: 'get',
    url: endpoint,
    baseURL: 'http://localhost:3000',
  }).then(({ data: { data } }) => data);
}
