// @flow
import React from 'react';
import type { Node } from 'react';

type Props = {
  value: number,
  name: string,
  onChange: (event: SyntheticEvent<HTMLSelectElement>) => void,
  options: Array<number>
}
const Select = ({
  value,
  name,
  onChange,
  options,
}: Props): Node => (
    <select
      value={value}
      name={name}
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
