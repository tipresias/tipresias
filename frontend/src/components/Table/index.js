// @flow
import React from 'react';
import type { Node } from 'react';
import styled from 'styled-components/macro';

const StyledTable = styled.table`
  width: 100%;
  border-collapse: collapse;
 `;

const StyledCaption = styled.caption`
  margin-bottom: .5rem;
  font-style: italic;
  text-align: left;
`;

const StyledTableHeading = styled.th`
font-weight: 700;
white-space: normal;
color: ${props => props.theme.colors.textColor};
border-bottom: 4px solid ${props => props.theme.colors.tableBorderColor};
padding: 0.5rem 0.75rem;
text-align: left;
`;

const StyledDataCell = styled.td`
border: 2px solid ${props => props.theme.colors.tableBorderColor};
padding: 0.75rem;
text-align: left;
`;

type svgType = {svg: boolean, text: string, path: string};

type TablePropsType = {
  caption: string,
  headers: Array<string>,
  rows: ?Array<Array<string | svgType>>
}

const Table = ({ caption, headers, rows }: TablePropsType): Node => {
  if (!rows || rows.length === 0) {
    return <div>Data not found</div>;
  }

  return (
    <StyledTable>
      {caption && <StyledCaption>{caption}</StyledCaption>}
      <tbody>
        <tr>
          {
            headers && headers.length > 0 && headers.map(item => (
              <StyledTableHeading scope="col" key={item}>{item}</StyledTableHeading>
            ))
          }
        </tr>
        {
          rows && rows.length > 0 && rows.map(row => (
            <tr key={Math.random()}>
              {row.map((value: any) => {
                const cellValue = value.svg ? (
                  <StyledDataCell key={value.svg + Math.random()}>
                    <img src={value.path} alt={value.text} width="24" />
                  </StyledDataCell>
                ) : (
                  <StyledDataCell key={value + Math.random()}>
                    {value}
                  </StyledDataCell>
                );
                return (cellValue);
              })}
            </tr>
          ))
        }
      </tbody>
    </StyledTable>
  );
};

export default Table;
