// @flow
import React from 'react';
import type { Node } from 'react';
import { dataTransformer } from './dataTransformer';

import type { LatestRoundPredictionsType } from '../../types';


type Props = {
  caption: string,
  headers: Array<string>,
  data: LatestRoundPredictionsType
}


const Table = ({ caption, headers, data }: Props): Node => {
  if (!data) {
    return <div>Data not found</div>;
  }
  const rows = dataTransformer(data);

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
};

export default Table;
