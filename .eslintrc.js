/** @type {import('eslint').Linter.Config} */
module.exports = {
  extends: ["@remix-run/eslint-config", "@remix-run/eslint-config/node"],
  rules: {
    // There are plenty of times when you want to make sure a hook just runs once,
    // so I don't find this rule particularly helpful
    'react-hooks/exhaustive-deps': "off"
  }
}
