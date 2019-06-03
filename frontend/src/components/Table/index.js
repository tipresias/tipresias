// @flow
import React from 'react';
import type { Node } from 'react';

import type { Row } from '../../types';

type Props = {
  caption: string,
  headers: Array<string>,
  rows: Array<Row>
}

const Table = ({ caption, headers, rows }: Props): Node => (
  <table>
    {caption && <caption>{caption}</caption>}
    <tbody>
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
