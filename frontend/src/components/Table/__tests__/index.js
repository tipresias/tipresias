import React from 'react';
import { shallow } from 'enzyme';
import Table from '../index';

describe('Table', () => {
  it('renders a table ', () => {
    const wrapper = shallow(<Table />);
    // expect to find a table tag as root of component
    expect(wrapper.find('table'));
  });

  it('sets the caption of the table when cation prop is passed', () => {
    const wrapper = shallow(<Table caption="table caption" />);
    // expect caption of table to be prop value passed to table component
    expect(wrapper.find('caption').text()).toBe('table caption');
  });

  it('sets the column headings when the headers prop is passed', () => {
    const wrapper = shallow(<Table headers={['header 1', 'header 2']} />);
    //  expect to find the first header th for te table columns with the value passed via headers props
    expect(wrapper.find('th').first().text()).toBe('header 1');
  });

  it('renders row items when rows prop is passed', () => {
    // arrange:
    const rowsMocked = [
      ['row 1 value 1', 'row 1 value 2', 'row 1 value 3'],
    ];
    const wrapper = shallow(<Table rows={rowsMocked} />);
    //  expect the row of the table tr to have 3 items passed via rows props
    expect(wrapper.find('tbody').childAt(1).children()).toHaveLength(3);
  });
});
