/** @type {import('@commitlint/types').UserConfig} */
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      ['feat', 'fix', 'docs', 'chore', 'refactor', 'test', 'build', 'ci', 'perf', 'style'],
    ],
    'scope-enum': [2, 'always', ['cli', 'dataset', 'website', 'plugin', 'docs', 'infra']],
    'scope-empty': [2, 'never'],
    'subject-case': [0],
  },
  ignores: [message => /^Merge /.test(message)],
}
