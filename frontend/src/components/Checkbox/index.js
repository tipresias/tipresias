// @flow
import React from 'react';
import type { Node } from 'react';

type Props = {
  label: string,
  id: string,
  name: string,
  value: string,
  onChange: (event: SyntheticEvent<HTMLSelectElement>) => void,
}
const Checkbox = ({
  label,
  id,
  name,
  value,
  onChange,
}: Props): Node => (
  <label htmlFor={id}>
    {label}
    <input
      type="checkbox"
      id={id}
      name={name}
      value={value}
      onChange={onChange}
    />
  </label>
);

export default Checkbox;
