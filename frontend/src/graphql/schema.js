// https://www.apollographql.com/docs/react/essentials/local-state/#client-side-schema
// following  https://codesandbox.io/s/r5qp83z0yq

// eslint-disable-next-line import/prefer-default-export
export const typeDefs = `
  extend type Theme {
    name: String
  }

  extend type Query {
    fetchTheme: Theme
  }

  extend type Mutation {
    setTheme(name: String!): Theme
  }
`;
