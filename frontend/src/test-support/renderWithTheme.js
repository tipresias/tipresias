import React from 'react';
import { shallow } from 'enzyme';
import { ThemeProvider } from 'styled-components';

function renderWithTheme(child, theme, render = shallow) {
  return render(child, {
    wrappingComponent: ({ children }) => <ThemeProvider theme={theme}>{children}</ThemeProvider>,
  });
}
export default renderWithTheme;
