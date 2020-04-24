import React from 'react';
import { shallow } from 'enzyme';
import ChartLoading from '../index';
// @todo refactor component to accept any component to render as Loading
describe('ChartLoading', () => {
  it('renders a default ChartLoading', () => {
    const wrapper = shallow(<ChartLoading text="loading..." />);
    expect(wrapper.find('ChartLoading__ChartLoadingStyled').text()).toBe('loading...');
  });
});
