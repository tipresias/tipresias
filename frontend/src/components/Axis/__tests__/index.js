import React from 'react';
import { shallow } from 'enzyme';
import Axis from '../index';

describe('Axis', () => {
  it('renders', () => {
    // arrange
    // act
    // const result = createBarGroups();
    // assert
    const wrapper = shallow(<Axis />);
    expect(wrapper).toMatchSnapshot();
  });
});
