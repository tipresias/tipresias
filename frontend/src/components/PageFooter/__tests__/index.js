import React from 'react';
import { mount } from 'enzyme';
import PageFooter from '../index';
// @todo add theme wrapper
describe('PageFooter', () => {
  it.skip('renders PageFooter', () => {
    const wrapper = mount(<PageFooter />);
    console.log(wrapper.debug());

    expect(wrapper).toMatchSnapshot();
  });
});
