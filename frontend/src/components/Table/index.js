// @flow
import React from 'react';
import type { Node } from 'react';
import { dataTransformer } from './dataTransformer';
import type { MatchesType } from '../../types';

type Props = {
  caption: string,
  headers: Array<string>,
  rows: MatchesType
}

const Table = ({ caption, headers, rows }: Props): Node => {
  if (!rows || rows.length === 0) {
    return <div>Data not found</div>;
  }
  const rowsArray = dataTransformer(rows);

  return (
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
          rowsArray && rowsArray.length > 0 && rowsArray.map(row => (
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
};

export default Table;
