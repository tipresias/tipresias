export const defaults = {
  themeName: 'light',
};

export const resolvers = {
  Mutation: {
    setTheme: (_, { themeName }, { cache }) => {
      const newThemeName = { themeName, __typeName: 'Theme' };
      const data = { themeName: newThemeName };
      cache.writeData({ data });
      return newThemeName;
    },
  },
};
