import React from 'react';
import { MockedProvider } from 'react-apollo/test-utils';
import { shallow, mount } from 'enzyme';
import MockComponent from '../../../test-support/MockComponent';
import App from '../index';
import Select from '../../../components/Select';
import { GET_PREDICTIONS_QUERY } from '../../../graphql';

jest.mock('../../BarChartContainer', () => MockComponent);
jest.mock('../../../components/ErrorBar', () => MockComponent);
jest.mock('../../../components/LoadingBar', () => MockComponent);
const waitForData = () => new Promise(resolve => setTimeout(resolve, 0));
const mocks = [
  {
    request: {
      query: GET_PREDICTIONS_QUERY,
      variables: {
        year: 2014,
      },
    },
    result: {
      data: {
        predictions: [{
          id: '1',
          match: {
            roundNumber: 1,
            year: 2014,
            teammatchSet: [
              {
                atHome: false,
                team: {
                  name: 'Fremantle',
                },
                score: 0,
              },
              {
                atHome: true,
                team: {
                  name: 'Collingwood',
                },
                score: 0,
              },
            ],
          },
          mlModel: {
            name: 'benchmark_estimator',
          },
          predictedWinner: {
            name: 'Fremantle',
          },
          predictedMargin: 6,
          isCorrect: false,
        }],
      },
    },
  },
];
const mocksWithError = [
  {
    request: {
      query: GET_PREDICTIONS_QUERY,
      variables: {
        year: 2014,
      },
    },
    error: new Error('Error'),
  },
];

describe('App container', () => {
  let shallowMountedApp;
  const app = () => {
    if (!shallowMountedApp) {
      shallowMountedApp = shallow(<App />);
    }
    return shallowMountedApp;
  };

  beforeEach(() => {
    shallowMountedApp = undefined;
  });

  it('always renders a div', () => {
    const divs = app().find('div');
    expect(divs.length).toBeGreaterThan(0);
  });

  it('always renders a Select', () => {
    const select = app().find(Select);
    expect(select.length).toBe(1);
  });

  it('sets the name prop of Select as `year`', () => {
    const select = app().find(Select);
    expect(select.props().name).toBe('year');
  });

  describe('when app\'s method `onChangeYear` is called', () => {
    it('Sets the rendered Select\'s `value` prop with updated `year` from state', () => {
      const event = {
        currentTarget: { value: '2015' },
      };
      app().instance().onChangeYear(event);
      app().update();

      const select = app().find(Select);
      expect(select.props().value).toBe(2015);
    });
  });
});

describe('App with apollo', () => {
  let props;
  let mountedAppWithApollo;

  const appWithApollo = () => {
    if (!mountedAppWithApollo) {
      mountedAppWithApollo = mount((<MockedProvider {...props}><App /></MockedProvider>));
    }
    return mountedAppWithApollo;
  };

  beforeEach(() => {
    mountedAppWithApollo = undefined;
  });

  describe('when is in initial state', () => {
    it('should render loading component', () => {
      props = { mocks: [] };
      const wrapper = appWithApollo();
      wrapper.update();
      const loadingBar = wrapper.find(MockComponent);
      expect(loadingBar.prop('text')).toBe('Loading predictions...');
    });
  });

  describe('when response is not 200', () => {
    it('should render Error', async () => {
      props = { mocks: mocksWithError };
      const wrapper = appWithApollo();
      await waitForData();
      wrapper.update();
      const ErrorBar = wrapper.find(MockComponent);
      expect(ErrorBar.prop('text')).toBe('Network error: Error');
    });
  });

  describe('when response is 200', () => {
    it('should render barChartContainer', async () => {
      props = { mocks, addTypename: false };
      const wrapper = appWithApollo();
      await waitForData();
      wrapper.update();
      const barChartContainer = wrapper.find(MockComponent);
      expect(barChartContainer.prop('games')).toEqual([{
        id: '1',
        match: {
          roundNumber: 1,
          year: 2014,
          teammatchSet: [
            {
              atHome: false,
              team: {
                name: 'Fremantle',
              },
              score: 0,
            },
            {
              atHome: true,
              team: {
                name: 'Collingwood',
              },
              score: 0,
            },
          ],
        },
        mlModel: {
          name: 'benchmark_estimator',
        },
        predictedWinner: {
          name: 'Fremantle',
        },
        predictedMargin: 6,
        isCorrect: false,
      }]);
    });
  });
});
