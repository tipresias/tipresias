import React from 'react';
import { shallow } from 'enzyme';
import StatusBar from '../index';
// @todo refactor component to accept any component to render default/empty/error message
describe('StatusBar', () => {
  it('renders a default StatusBar', () => {
    const wrapper = shallow(<StatusBar text="loading..." />);
    expect(wrapper.find('StatusBar__DefaultStatusStyled').text()).toBe('loading...');
  });

  it('renders an empty mesage StatusBar', () => {
    const wrapper = shallow(<StatusBar text="no data" empty />);
    expect(wrapper.find('StatusBar__EmptyStatusStyled').text()).toBe('no data');
  });

  it('renders an error StatusBar', () => {
    const wrapper = shallow(<StatusBar text="error message" error />);
    expect(wrapper.find('StatusBar__ErrorStatusStyled').text()).toBe('error message');
  });
});
