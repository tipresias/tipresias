// @flow
import React, { Fragment } from 'react';
import type { Node } from 'react';
import { DefinitionListStyled, DefinitionTermStyled, DefinitionDescriptionStyled } from './style';

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
    <DefinitionListStyled>
      {
        items && items.length > 0 && items.map(item => (
          <Fragment key={item.id}>
            <DefinitionTermStyled>{item.key}</DefinitionTermStyled>
            <DefinitionDescriptionStyled>{item.value}</DefinitionDescriptionStyled>
          </Fragment>
        ))
      }
    </DefinitionListStyled>
  );
};

export default DefinitionList;
