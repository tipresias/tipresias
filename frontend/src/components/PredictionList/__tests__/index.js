import React from 'react';
import { shallow } from 'enzyme';
import PredictionList from '../index';

describe('PredictionList', () => {
  it('renders a list', () => {
    const itemsMocked = [
      {
        match: 1,
        teams: [
          {
            name: 'team ABC', isHome: true, predictedMargin: 35,
          },
          {
            name: 'team DEF', isHome: false, predictedMargin: null,
          }],
      },
    ];
    const wrapper = shallow(<PredictionList items={itemsMocked} />);
    expect(wrapper.find('style__List').length).toBe(1);
  });

  it('renders match items if items prop is passed', () => {
    const itemsMocked = [
      {
        match: 1,
        teams: [
          {
            name: 'team ABC', isHome: true, predictedMargin: 35,
          },
          {
            name: 'team DEF', isHome: false, predictedMargin: null,
          }],
      },
    ];
    const wrapper = shallow(<PredictionList items={itemsMocked} />);
    expect(wrapper.find('style__List').children().length).toBe(1);
  });

  it('renders message when items prop is not passed', () => {
    const wrapper = shallow(<PredictionList />);
    expect(wrapper.childAt(0).text()).toBe('no data found');
  });

  it('renders message when items prop is empty', () => {
    const wrapper = shallow(<PredictionList items={[]} />);
    expect(wrapper.childAt(0).text()).toBe('no data found');
  });
});
