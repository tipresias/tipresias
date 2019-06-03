import React from 'react';
import { shallow } from 'enzyme';
import DefinitionList from '../index';

describe('DefinitionList', () => {
  let itemsMocked;

  beforeEach(() => {
    itemsMocked = [
      {
        id: 1,
        key: 'key 1',
        value: 123,
      },
      {
        id: 2,
        key: 'key 2',
        value: 'ABC',
      },
    ];
  });

  it('renders a definition list', () => {
    const wrapper = shallow(<DefinitionList items={itemsMocked} />);
    expect(wrapper.find('style__DefinitionListStyled').length).toBe(1);
  });

  it('renders items if items prop is passed', () => {
    const wrapper = shallow(<DefinitionList items={itemsMocked} />);
    expect(wrapper.find('style__DefinitionListStyled').children().length).toBe(4);
  });

  it('renders message when items prop is not passed', () => {
    const wrapper = shallow(<DefinitionList />);
    expect(wrapper.childAt(0).text()).toBe('No items found');
  });

  it('renders message when items prop is empty', () => {
    const wrapper = shallow(<DefinitionList items={[]} />);
    expect(wrapper.childAt(0).text()).toBe('No items found');
  });
});
