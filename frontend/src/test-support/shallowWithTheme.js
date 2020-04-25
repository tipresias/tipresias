import React from 'react';
import { shallow } from 'enzyme';
import { ThemeProvider } from 'styled-components';

function shallowWithTheme(child, theme) {
  return shallow(child, {
    wrappingComponent: ({ children }) => <ThemeProvider theme={theme}>{children}</ThemeProvider>,
  });
}
export default shallowWithTheme;
