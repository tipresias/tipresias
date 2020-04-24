import React from 'react';
import { shallow } from 'enzyme';
import Checkbox from '../index';

describe('Checkbox', () => {
  const onChangeSpy = jest.fn();
  it('renders a checkbox with a label', () => {
    const wrapper = shallow(<Checkbox label="Checkbox_label" id="Checkbox_id" name="name" value="value" onChange={onChangeSpy} />);
    expect(wrapper.find('input[type="checkbox"]').exists()).toBe(true);
    expect(wrapper.find('label').exists()).toBe(true);
  });

  it('label is associated to the checkbox', () => {
    const wrapper = shallow(<Checkbox label="Checkbox_label" id="Checkbox_id" name="name" value="value" onChange={onChangeSpy} />);
    expect(wrapper.find('input[id="Checkbox_id"]').prop('id')).toBe('Checkbox_id');
    expect(wrapper.find('label[htmlFor="Checkbox_id"]').prop('htmlFor')).toBe('Checkbox_id');
  });

  it('uses the label value passed', () => {
    const wrapper = shallow(<Checkbox label="Checkbox_label" id="Checkbox_id" name="name" value="value" onChange={onChangeSpy} />);
    expect(wrapper.find('label').text()).toBe('Checkbox_label');
  });

  it('when checked calls onChange', () => {
    const eventObjectMocked = { target: { value: 'Checkbox_name123' } };
    const wrapper = shallow(<Checkbox label="Checkbox_label" id="Checkbox_id" name="Checkbox_name" value="Checkbox_name" onChange={onChangeSpy} />);
    wrapper.find('input[id="Checkbox_id"]').simulate('change', eventObjectMocked);
    expect(onChangeSpy).toHaveBeenCalledWith({ target: { value: 'Checkbox_name123' } });
  });
});
