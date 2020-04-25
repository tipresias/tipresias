import React from 'react';
import { StaticRouter } from 'react-router-dom';
import mountWithTheme from '../../../test-support/mountWithTheme';
import PageFooter from '../index';

const TEST_THEME = {
  colors: {
    textColor: 'black',
    logoFilter: 'inherit',
  },
};
const PageFooterWithRouter = () => (<StaticRouter location="someLocation"><PageFooter /></StaticRouter>);

describe('PageFooter', () => {
  it('renders PageFooter', () => {
    const wrapper = mountWithTheme(<PageFooterWithRouter />, TEST_THEME);
    expect(wrapper.html()).toMatchSnapshot();
  });
});
