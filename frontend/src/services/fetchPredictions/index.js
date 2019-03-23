// @flow
import axios from 'axios';

export default function fetchPredictions(endpoint: string) {
  return axios({
    method: 'get',
    url: endpoint,
  }).then(({ data: { data } }) => data);
}
