import React from 'react';
import { shallow } from 'enzyme';
import ErrorBoundary from '../index';

// @todo add test for error
describe('ErrorBoundary', () => {
  it.skip('renders a ErrorBoundary', () => {
    const wrapper = shallow(<ErrorBoundary />);
    console.log(wrapper);

    expect(true).toBe(true);
  });
});
