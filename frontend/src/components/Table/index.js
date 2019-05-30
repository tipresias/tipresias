// @flow
import React from 'react';
import type { Node } from 'react';

type Props = {
  caption: string,
  headers: Array<string>,
  rows: Array<Array>
}

const Table = ({ caption, headers, rows }: Props): Node => (
  <table>
    <tbody>
      {caption && <caption>{caption}</caption>}
      <tr>
        {
          headers && headers.length > 0 && headers.map(item => (
            <th scope="col" key={item}>{item}</th>
          ))
        }
      </tr>

      {
        rows && rows.length > 0 && rows.map(row => (
          <tr key={Math.random()}>
            {row.map(value => (
              <td key={value}>{value}</td>
            ))}
          </tr>
        ))
      }
    </tbody>

  </table>
);

export default Table;
