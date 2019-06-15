import React from 'react';
import { shallow } from 'enzyme';
import Table from '../index';

jest.mock('../dataTransformer', () => ({
  dataTransformer: () => [['2018-09-28', 'mocked predicted winner name', 'mocked predicted margin value', 'mocked predicted loser name', 'yes']],
}));

let wrapper;
let mockedProps;

const getWrapperShallow = props => shallow(<Table {...props} />);

describe('Table', () => {
  beforeEach(() => {
    mockedProps = {
      data: {
        roundNumber: 1,
        matches: [{
          startDateTime: 'mock data',
          homeTeam: {},
          awayTeam: {},
          predictions: [],
        }],
      },
      caption: 'mocked table caption',
      headers: ['Date', 'Predicted Winner', 'Predicted margin', 'Predicted Loser', 'is Correct?'],
    };
    wrapper = getWrapperShallow(mockedProps);
  });

  it('renders a table ', () => {
    // expect to find a table tag as root of component
    expect(wrapper.find('table').length).toBe(1);
  });

  it('renders no table when data prop is not passed ', () => {
    // overwriting a prop value to null
    mockedProps.data = null;

    // act
    wrapper = getWrapperShallow(mockedProps);

    // expect to find a table tag as root of component
    expect(wrapper.find('table').length).toBe(0);
  });

  it('sets the caption of the table when cation prop is passed', () => {
    // expect caption of table to be prop value passed to table component
    expect(wrapper.find('caption').text()).toBe('mocked table caption');
  });

  it('sets the column headings when the headers prop is passed', () => {
    /* expect to find the first header th for te table columns
    with the value passed via headers props */
    expect(wrapper.find('th').first().text()).toBe('Date');
    expect(wrapper.find('th').last().text()).toBe('is Correct?');
  });

  it('renders row items when rows prop is passed', () => {
    //  expect the row of the table tr to have 3 items passed via rows props
    expect(wrapper.find('tbody').childAt(1).children()).toHaveLength(5);
  });
});
