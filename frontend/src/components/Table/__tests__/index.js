import React from 'react';
import { shallow } from 'enzyme';
import Table from '../index';

let wrapper;
let mockedProps;

const getWrapperShallow = props => shallow(<Table {...props} />);

describe('Table', () => {
  beforeEach(() => {
    mockedProps = {
      caption: 'tipresias_2020 predictions for matches of round 1, season 2020',
      headers: [
        'Date',
        'Predicted Winner',
        'Predicted margin',
        'Win probability',
        'is Correct?',
      ],
      rows: [
        [
          '2020-03-19',
          'Richmond',
          '23',
          '0.92',
          {
            svg: true,
            text: 'correct',
            path: '/static/media/icon_check.954fc6fb.svg',
          },
        ],
        [
          '2020-03-20',
          'Collingwood',
          '16',
          '0.56',
          {
            svg: true,
            text: 'correct',
            path: '/static/media/icon_check.954fc6fb.svg',
          },
        ],
        [
          '2020-03-21',
          'Essendon',
          '8',
          '0.66',
          {
            svg: true,
            text: 'correct',
            path: '/static/media/icon_check.954fc6fb.svg',
          },
        ],
        [
          '2020-03-21',
          'Adelaide',
          '10',
          '0.52',
          {
            svg: true,
            text: 'incorrect',
            path: '/static/media/icon_cross.6c3e39ad.svg',
          },
        ],
        [
          '2020-03-21',
          'Port Adelaide',
          '17',
          '0.96',
          {
            svg: true,
            text: 'correct',
            path: '/static/media/icon_check.954fc6fb.svg',
          },
        ],
        [
          '2020-03-21',
          'GWS',
          '3',
          '0.59',
          {
            svg: true,
            text: 'correct',
            path: '/static/media/icon_check.954fc6fb.svg',
          },
        ],
        [
          '2020-03-22',
          'North Melbourne',
          '29',
          '0.78',
          {
            svg: true,
            text: 'correct',
            path: '/static/media/icon_check.954fc6fb.svg',
          },
        ],
        [
          '2020-03-22',
          'Brisbane',
          '4',
          '0.65',
          {
            svg: true,
            text: 'incorrect',
            path: '/static/media/icon_cross.6c3e39ad.svg',
          },
        ],
        [
          '2020-03-22',
          'West Coast',
          '30',
          '0.9',
          {
            svg: true,
            text: 'correct',
            path: '/static/media/icon_check.954fc6fb.svg',
          },
        ],
      ],
    };
    wrapper = getWrapperShallow(mockedProps);
  });

  it('renders a table ', () => {
    // expect to find a table tag as root of component
    expect(wrapper.find('Table__StyledTable').length).toBe(1);
  });

  it('renders no table when data prop is not passed ', () => {
    // overwriting a prop value to null
    mockedProps.rows = null;

    // act
    wrapper = getWrapperShallow(mockedProps);

    // expect to find a table tag as root of component
    expect(wrapper.find('Table__StyledTable').length).toBe(0);
    expect(wrapper.find('div').text()).toBe('Data not found');
  });

  it('sets the caption of the table when cation prop is passed', () => {
    // expect caption of table to be prop value passed to table component
    expect(wrapper.find('Table__StyledCaption').text()).toBe('tipresias_2020 predictions for matches of round 1, season 2020');
  });

  it('sets the column headings when the headers prop is passed', () => {
    /* expect to find the first header th for te table columns
    with the value passed via headers props */
    expect(wrapper.find('Table__StyledTableHeading').first().text()).toBe('Date');
    expect(wrapper.find('Table__StyledTableHeading').last().text()).toBe('is Correct?');
  });

  it('renders row items when rows prop is passed', () => {
    //  expect the row of the table tr to have 3 items passed via rows props
    expect(wrapper.find('tbody').childAt(1).children()).toHaveLength(5);
  });
});
