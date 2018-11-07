import React from 'react';
import { shallow } from 'enzyme';
import BarChartContainer from '../index';

describe('BarChartContainer', () => {
  it('renders correctly', () => {
    const wrapper = shallow(<BarChartContainer />);
    expect(wrapper).toMatchSnapshot();
  });
});
