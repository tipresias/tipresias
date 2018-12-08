import React from 'react';
import { shallow } from 'enzyme';
import BarChart from '../index';

describe('BarChart', () => {
  it('renders correctly', () => {
    const barsMocked = [
      [
        {
          key: '1-oddsmakers',
          round: 1,
          x: 7.857142857142858,
          y: 368.2352941176471,
          height: 11.764705882352928,
          width: 6,
          fill: '#1f77b4',
        },
        {
          key: '1-tipresias_betting',
          round: 1,
          x: 13.857142857142858,
          y: 368.2352941176471,
          height: 11.764705882352928,
          width: 6,
          fill: '#ff7f0e',
        },
        {
          key: '1-tipresias_match',
          round: 1,
          x: 19.857142857142858,
          y: 370.5882352941176,
          height: 9.411764705882376,
          width: 6,
          fill: '#2ca02c',
        },
        {
          key: '1-tipresias_player',
          round: 1,
          x: 25.857142857142858,
          y: 361.1764705882353,
          height: 18.823529411764696,
          width: 6,
          fill: '#d62728',
        },
      ],
    ];
    const wrapper = shallow(<BarChart bars={barsMocked} />);
    expect(wrapper).toMatchSnapshot();
  });
});
