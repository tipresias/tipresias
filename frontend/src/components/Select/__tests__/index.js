import React from 'react';
import { shallow } from 'enzyme';
import Select from '../index';

describe('select', () => {
  it('renders', () => {
    // arrange
    const optionsMocked = [];
    // act
    // const result = createBarGroups();
    // assert
    const wrapper = shallow(<Select value={value} onChange={onChange} options={optionsMocked} />);
    expect(wrapper).toMatchSnapshot();
  });
});
