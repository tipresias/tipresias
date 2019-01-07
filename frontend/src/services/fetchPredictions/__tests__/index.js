import nock from 'nock';
import axios from 'axios';
import httpAdapter from 'axios/lib/adapters/http';
import fetchPredictions from '../index';

const host = 'http://localhost:3000';
axios.defaults.host = host;
axios.defaults.adapter = httpAdapter;

describe('fetchPredictions', () => {
  it('sends a HTTP request with method set as GET', () => {
    // arrange
    const endpoint = '/fake/endpoint';

    const scope = nock(host)
      .get(endpoint)
      .reply(200, '{"lorem":"ipsum"}');

    // act
    return fetchPredictions().then(() => {
      // assert
      expect(scope.isDone()).toBe(true);
    });
  });
});
