import nock from 'nock';
import axios from 'axios';
import httpAdapter from 'axios/lib/adapters/http';
import fetchPredictions from '../index';

const host = 'http://localhost:3000';
axios.defaults.host = host;
axios.defaults.adapter = httpAdapter;
axios.defaults.baseURL = host;

describe('fetchPredictions', () => {
  it('sends a HTTP request with endpoint passed as argument', () => {
    // arrange
    const mockEndpoint = '/mock/endpoint';

    const scope = nock(host)
      .get(mockEndpoint)
      .reply(200, '{"lorem":"ipsum"}');

    // act
    return fetchPredictions('/mock/endpoint').then(() => {
      // assert
      expect(scope.isDone()).toBe(true);
    });
  });
});
