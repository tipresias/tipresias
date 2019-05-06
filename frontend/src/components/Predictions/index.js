import React from 'react';
import { Query } from 'react-apollo';
import { gql } from 'apollo-boost';

const Predictions = () => (
  <Query
    query={gql`
    {
      predictions(year: 2016){
        id
        match {
          venue
        }
      }
    }
    `}
  >
    {
      ({ loading, error, data }) => {
        if (loading) return <p>Loading...</p>;
        if (error) return <p>Error :(</p>;

        return data.predictions.map(item => (
          <div key={item.id}>
            <p>
venue:
              {item.match.venue}
            </p>
          </div>
        ));
      }
    }
  </Query>
);

export default Predictions;
