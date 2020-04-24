import React from 'react';
import { shallow } from 'enzyme';
import Fieldset from '../index';

describe('Fieldset', () => {
  it('renders a legend text', () => {
    const wrapper = shallow(<Fieldset legend="legend text" />);
    expect(wrapper.find('Fieldset__LegendStyled').text()).toBe('legend text');
  });

  it('renders children', () => {
    const wrapper = shallow(<Fieldset legend="legend text"><div>fieldset children</div></Fieldset>);
    expect(wrapper.find('div').text()).toBe('fieldset children');
  });
});
