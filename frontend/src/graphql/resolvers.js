import { FETCH_THEME } from './index';

export const defaults = {
  fetchTheme: { name: 'light', __typename: 'Theme' },
};

export const resolvers = {
  Mutation: {
    setTheme: (_, { name }, { cache }) => {
      const newFetchTheme = { name, __typename: 'Theme' };
      const data = { fetchTheme: newFetchTheme };
      cache.writeData({
        query: FETCH_THEME,
        data,
      });
      return newFetchTheme;
    },
  },
};
