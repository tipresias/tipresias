import React from 'react';
import { shallow } from 'enzyme';
import LineChartMain from '../index';

describe('LineChartMain', () => {
  let MOCKED_PROPS;
  let wrapper;

  beforeEach(() => {
    MOCKED_PROPS = {
      models: [
        'benchmark_estimator',
        'confidence_estimator',
        'tipresias_2019',
        'tipresias_2020',
      ],
      xAxis: {
        dataKey: 'roundNumber',
        label: 'Rounds',
      },
      yAxis: {
        label: 'Accuracy %',
      },
      data: [
        {
          roundNumber: 1,
          benchmark_estimator: 77.78,
          confidence_estimator: 88.89,
          tipresias_2019: 77.78,
          tipresias_2020: 77.78,
        },
      ],
    };

    wrapper = shallow(<LineChartMain {...MOCKED_PROPS} />);
  });

  it('renders a line chart with data prop', () => {
    expect(wrapper.find('LineChart').exists()).toBe(true);
    expect(wrapper.find('LineChart').prop('data')).toEqual(MOCKED_PROPS.data);
  });

  it('renders X and Y axis with the correct label', () => {
    expect(wrapper.find('XAxis').prop('label').value).toBe('Rounds');
    expect(wrapper.find('YAxis').prop('label').value).toBe('Accuracy %');
  });

  it('renders X axis with the correct datakey', () => {
    expect(wrapper.find('XAxis').prop('dataKey')).toBe('roundNumber');
  });

  it('renders a line per each model passed', () => {
    expect(wrapper.find('Line').length).toBe(4);
  });
});
