import React from 'react';
import { shallow } from 'enzyme';
import Select from '../index';

describe('select', () => {
  it('renders', () => {
    // arrange
    // props:
    const optionsMocked = ['item1', 'item2', 'item3'];
    const valueMocked = 'mocked_value';
    const onChangeMocked = () => { console.log('onChange'); };

    // act
    const wrapper = shallow(<Select
      value={valueMocked}
      onChange={onChangeMocked}
      options={optionsMocked}
    />);

    // assert
    expect(wrapper).toMatchSnapshot();
  });
});
