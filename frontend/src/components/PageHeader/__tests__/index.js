import React from 'react';
import { shallow } from 'enzyme';
import PageHeader from '../index';

describe('PageHeader', () => {
  it('renders PageHeader', () => {
    const wrapper = shallow(<PageHeader links={[{ url: '/about', text: 'About' }]} />);
    expect(wrapper).toMatchSnapshot();
  });

  it('renders PageHeader with children', () => {
    const wrapper = shallow(
      <PageHeader links={[{ url: '/about', text: 'About' }]}>
        <input
          className="favorite styled"
          type="button"
          value="Add to favorites"
        />
      </PageHeader>,
    );
    expect(wrapper.find('input[type="button"]').exists()).toBe(true);
  });
});
