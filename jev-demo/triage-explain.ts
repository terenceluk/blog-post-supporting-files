import { readFileSync } from 'node:fs'
import { experimental_evaluate as evaluate } from 'ai'

async function main() {
  const alert = JSON.parse(readFileSync('sample-alert.json', 'utf8'))

  const result = await evaluate({
    model: 'typesafe-ai/jev',
    state: alert,
    questions: {
      manyAccounts: {
        type: 'boolean',
        instructions: 'Do the failed sign-ins span a large number of distinct user accounts?',
      },
      fewSourceIps: {
        type: 'boolean',
        instructions: 'Do the failed sign-ins come from a small number of source IP addresses?',
      },
      invalidPasswordErrors: {
        type: 'boolean',
        instructions: 'Are the failures mostly invalid username or password errors rather than MFA or policy failures?',
      },
      securityRelated: {
        type: 'boolean',
        instructions: 'Could this alert indicate malicious activity that the security team should review?',
      },
    },
  })

  for (const [name, answer] of Object.entries(result.answers)) {
    if (answer.type === 'boolean') {
      console.log(`${name.padEnd(24)} ${answer.probability.toFixed(2)}`)
    }
  }
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})