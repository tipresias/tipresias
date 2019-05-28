import React from 'react';
import { shallow } from 'enzyme';
import Select from '../index';

describe('select', () => {
  it('renders', () => {
    // arrange
    const optionsMocked = ['item1', 'item2', 'item3'];
    const valueMocked = 'mocked_value';
    const onChangeSpy = jest.fn();

    // act
    const wrapper = shallow(<Select
      value={valueMocked}
      onChange={onChangeSpy}
      options={optionsMocked}
    />);

    // assert
    expect(wrapper).toMatchSnapshot();
  });

  it('calls onChange callback when select onChange is executed', () => {
    const optionsMocked = ['item1', 'item2', 'item3'];
    const valueMocked = 'mocked_value';
    const onChangeSpy = jest.fn();
    const eventObjectMocked = { target: { value: 'ok' } };
    const wrapper = shallow(<Select
      value={valueMocked}
      onChange={onChangeSpy}
      options={optionsMocked}
    />);
    wrapper.find('select').simulate('change', eventObjectMocked);
    expect(onChangeSpy).toHaveBeenCalledWith(eventObjectMocked);
  });
  it('sets the value prop when value prop is passed', () => {
    const optionsMocked = ['item1', 'item2', 'item3'];
    const valueMocked = 'mocked_value';
    const onChangeSpy = jest.fn();
    const wrapper = shallow(<Select
      value={valueMocked}
      onChange={onChangeSpy}
      options={optionsMocked}
    />);
    expect(wrapper.find('select').props().value).toBe('mocked_value');
  });
});
