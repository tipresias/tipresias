// @flow
import React from 'react';
import type { Node } from 'react';

type Props = {
  value: number,
  onChange: (event: any)=> void,
  options: Array<number>
}
const Select = ({
  value,
  onChange,
  options = [2011, 2012, 2013, 2014],
}: Props): Node => (
  <select
    value={value}
    name="year"
    onChange={onChange}
  >
    {
      options.map(option => (
        <option key={option} value={option}>
          {option}
        </option>))
    }
  </select>
);

export default Select;
