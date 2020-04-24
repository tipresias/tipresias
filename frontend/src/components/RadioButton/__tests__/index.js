import React from 'react';
import { shallow } from 'enzyme';
import RadioButton from '../index';

describe('RadioButton', () => {
  const onChangeSpy = jest.fn();

  it('renders a RadioButton with a label', () => {
    const wrapper = shallow(<RadioButton label="RadioButton_label" id="RadioButton_id" name="name" value="value" onChange={onChangeSpy} />);
    expect(wrapper.find('input[type="radio"]').exists()).toBe(true);
    expect(wrapper.find('label').exists()).toBe(true);
  });

  it('label is associated to the RadioButton', () => {
    const wrapper = shallow(<RadioButton label="RadioButton_label" id="RadioButton_id" name="name" value="value" onChange={onChangeSpy} />);
    expect(wrapper.find('input[id="RadioButton_id"]').prop('id')).toBe('RadioButton_id');
    expect(wrapper.find('label[htmlFor="RadioButton_id"]').prop('htmlFor')).toBe('RadioButton_id');
  });

  it('uses the label value passed', () => {
    const wrapper = shallow(<RadioButton label="RadioButton_label" id="RadioButton_id" name="name" value="value" onChange={onChangeSpy} />);
    expect(wrapper.find('label').text()).toBe('RadioButton_label');
  });


  it('when checked calls onChange', () => {
    const eventObjectMocked = { target: { value: 'RadioButton_name123' } };
    const wrapper = shallow(<RadioButton label="RadioButton_label" id="RadioButton_id" name="RadioButton_name" value="RadioButton_name" onChange={onChangeSpy} />);
    wrapper.find('input[id="RadioButton_id"]').simulate('change', eventObjectMocked);
    expect(onChangeSpy).toHaveBeenCalledWith({ target: { value: 'RadioButton_name123' } });
  });
});
