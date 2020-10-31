import React from 'react';
import { StaticRouter } from 'react-router-dom';
import { mount } from 'enzyme';
import renderWithTheme from '../../../test-support/renderWithTheme';
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
    const wrapper = renderWithTheme(<PageFooterWithRouter />, TEST_THEME, mount);
    expect(wrapper.html()).toMatchSnapshot();
  });
});
