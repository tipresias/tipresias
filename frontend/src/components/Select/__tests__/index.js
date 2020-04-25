import React from 'react';
import { shallow } from 'enzyme';
import Select from '../index';

describe('select', () => {
  it.skip('renders', () => {
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
      name="test_select"
      id="test_select1"
      label="choose an option"
    />);
    wrapper.find('Select__SelectStyled').simulate('change', eventObjectMocked);
    expect(onChangeSpy).toHaveBeenCalledWith({ target: { value: 'ok' } });
  });

  it('sets the value prop when value prop is passed', () => {
    const optionsMocked = ['item1', 'item2', 'item3'];
    const valueMocked = 'mocked_value';
    const onChangeSpy = jest.fn();
    const wrapper = shallow(<Select
      value={valueMocked}
      onChange={onChangeSpy}
      options={optionsMocked}
      name="test_select"
      id="test_select1"
      label="choose an option"
    />);
    expect(wrapper.find('Select__SelectStyled').props().value).toBe('mocked_value');
  });
});
