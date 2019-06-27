import React, { Fragment } from 'react';
import { GlossaryStyled, DescriptionStyled } from './style';
import allTerms from './index.json';

class Glossary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      items: [],
    };
  }

  componentDidMount() {
    this.setState({ items: allTerms });
  }

  render() {
    const { items } = this.state;
    return (
      <GlossaryStyled>
        <h2>Terms used in Tipresias:</h2>
        <dl>
          {
            items.length > 0 && items.map(
              item => (
                <Fragment key={item.id}>
                  <dt>{item.term}</dt>
                  <DescriptionStyled>{item.description}</DescriptionStyled>
                </Fragment>
              ),
            )
          }
        </dl>
      </GlossaryStyled>
    );
  }
}


export default Glossary;
