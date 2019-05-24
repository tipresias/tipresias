// @flow
import React from 'react';
import type { Node } from 'react';

type Props = {
  name: string,
  value: number,
  onChange: (event: SyntheticEvent<HTMLSelectElement>) => void,
  options: Array<number>
}
const Select = ({
  name,
  value,
  onChange,
  options,
}: Props): Node => (
  <select
    name={name}
    value={value}
    onChange={onChange}
  >
    {
      options.map(option => (
        <option key={option} value={option}>
          {option}
        </option>
      ))
    }
  </select>
);

export default Select;
