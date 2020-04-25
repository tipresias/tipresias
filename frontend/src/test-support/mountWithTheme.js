import React from 'react';
import { mount } from 'enzyme';
import { ThemeProvider } from 'styled-components';

function mountWithTheme(child, theme) {
  return mount(child, {
    wrappingComponent: ({ children }) => <ThemeProvider theme={theme}>{children}</ThemeProvider>,
  });
}
export default mountWithTheme;
