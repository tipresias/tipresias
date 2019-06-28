// https://www.apollographql.com/docs/react/essentials/local-state/#client-side-schema
// following  https://codesandbox.io/s/r5qp83z0yq

const typeDefs = `
  type Theme {
    themeName: String
  }

  type Query {
    fetchTheme: Theme
  }

  type Mutation {
    setTheme(themeName: String!): String
  }
`;

export default typeDefs;
