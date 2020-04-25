import React from 'react';
import shallowWithTheme from '../../../test-support/shallowWithTheme';
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
    const wrapper = shallowWithTheme(
      <PageHeader links={[{ url: '/about', text: 'About' }]} />,
      TEST_THEME,
    );
    expect(wrapper.find('PageHeader__ListStyled').children().length).toBe(1);
  });

  it('renders PageHeader with children', () => {
    const wrapper = shallowWithTheme(
      <PageHeader links={[{ url: '/about', text: 'About' }]}>
        <input
          className="favorite styled"
          type="button"
          value="Add to favorites"
        />
      </PageHeader>,
      TEST_THEME,
    );
    expect(wrapper.find('input[type="button"]').exists()).toBe(true);
  });
});
