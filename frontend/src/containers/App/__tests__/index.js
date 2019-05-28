import React from 'react';
import { MockedProvider } from 'react-apollo/test-utils';
import { shallow, mount } from 'enzyme';
import MockComponent from '../../../test-support/MockComponent';
import GET_PREDICTIONS_QUERY from '../../../graphql/getPredictions';
import App from '../index';
import Select from '../../../components/Select';

jest.mock('../../../components/BarChartMain', () => MockComponent);
jest.mock('../../../components/StatusBar', () => MockComponent);
jest.mock('../../../components/BarChartLoading', () => MockComponent);
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
    it('should render BarChartLoading component', () => {
      props = { mocks: [] };
      const wrapper = appWithApollo();
      wrapper.update();
      const BarChartLoading = wrapper.find(MockComponent);
      expect(BarChartLoading.prop('text')).toBe('Loading predictions...');
    });
  });

  describe.skip('when response is not 200', () => {
    it('should render Error', async () => {
      props = { mocks: mocksWithError };
      const wrapper = appWithApollo();
      await waitForData();
      wrapper.update();
      const StatusBar = wrapper.find(MockComponent);
      expect(StatusBar.prop('error')).toBe(true);
    });
  });

  describe.skip('when response is 200', () => {
    it('should render BarChartMain', async () => {
      props = { mocks, addTypename: false };
      const wrapper = appWithApollo();
      await waitForData();
      wrapper.update();
      const BarChartMain = wrapper.find(MockComponent);
      expect(BarChartMain.prop('data').length).toBe(1);
    });
  });
});
