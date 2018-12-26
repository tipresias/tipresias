// @flow
import React from 'react';
import type { Node } from 'react';

type Props = {
  value: number,
  onChange: (event: SyntheticEvent<HTMLSelectElement>)=> void,
  options: Array<number>
}
const Select = ({
  value,
  onChange,
  options,
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
