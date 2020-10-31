import Rollbar from 'rollbar';

const rollbar = new Rollbar({
  accessToken: '835ffffd575e46afbfb0dfeb1c6141cb',
  captureUncaught: true,
  captureUnhandledRejections: true,
  enabled: process.env.NODE_ENV === 'production',
});

// eslint-disable-next-line import/prefer-default-export
export const log = {
  error: (error) => {
    console.error(error);
    rollbar.error(error);
  },
  warning: (warning) => {
    console.warn(warning);
    rollbar.warning(warning);
  },
  info: message => console.log(message),
};
