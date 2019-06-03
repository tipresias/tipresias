// @flow
import React, { Fragment } from 'react';
import type { Node } from 'react';

type Definition = {
  id: number,
  key: string,
  value: any
}

type Props = {
  items: Array<Definition>
}

const DefinitionList = ({ items }: Props): Node => {
  if (!items || items.length === 0) { return (<p>No items found</p>); }
  return (
    <dl>
      {
        items && items.length > 0 && items.map(item => (
          <Fragment key={item.id}>
            <dt>{item.key}</dt>
            <dd>{item.value}</dd>
          </Fragment>
        ))
      }
    </dl>
  );
};

export default DefinitionList;
