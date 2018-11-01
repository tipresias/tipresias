import React from 'react';

const Select = ({
  value,
  onChange,
  options = [2011, 2012, 2013, 2014],
}) => (
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
