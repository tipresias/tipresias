import React from 'react';
import renderWithTheme from '../../../test-support/renderWithTheme';
import PageHeader from '../index';

// @todo check jest-styled-components and  enzyme-to-json why this packages are not working

const TEST_THEME = {
  colors: {
    textColor: 'white',
    logoFilter: 'inherit',
    widgetBorderColor: 'white',
  },
};

describe('PageHeader', () => {
  it('renders PageHeader', () => {
    const wrapper = renderWithTheme(
      <PageHeader links={[{ url: '/about', text: 'About' }]} />,
      TEST_THEME,
    );
    expect(wrapper.find('PageHeader__ListStyled').children().length).toBe(2);
  });

  it('renders PageHeader with toggle button', () => {
    const wrapper = renderWithTheme(
      <PageHeader links={[{ url: '/about', text: 'About' }]} />,
      TEST_THEME,
    );

    expect(wrapper.find('PageHeader__ToggleThemeButton').exists()).toBe(true);
  });
});
