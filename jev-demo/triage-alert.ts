import { readFileSync } from 'node:fs'
import { experimental_evaluate as evaluate, type JSONValue } from 'ai'

const CONFIDENCE_FLOOR = 0.6
const PROBABILITY_FLOOR = 0.7

async function triage(alert: Record<string, JSONValue>) {
  const result = await evaluate({
    model: 'typesafe-ai/jev',
    state: alert,
    questions: {
      category: {
        type: 'choice',
        instructions: 'Which operations queue should own this Azure Monitor alert?',
        criteria: {
          identity: 'Entra ID sign-ins, Conditional Access, MFA, and account lockouts',
          network: 'Virtual networks, firewalls, VPN, ExpressRoute, DNS, and load balancers',
          compute: 'Virtual machines, App Service, Functions, and container workloads',
          data: 'Storage accounts, SQL, Cosmos DB, and backups',
          cost: 'Budgets, spend anomalies, and quota',
        },
      },
      urgency: {
        type: 'score',
        instructions:
          'How urgent is this alert based on its actual content, regardless of the severity configured on the rule?',
        criteria: [
          'Informational, no action needed',
          'Low, review during business hours',
          'Moderate, investigate today',
          'High, investigate within the hour',
          'Critical, active incident requiring immediate response',
        ],
      },
      securityRelated: {
        type: 'boolean',
        instructions: 'Could this alert indicate malicious activity that the security team should review?',
        criteria: {
          true: 'The pattern is consistent with an attack, compromise, or abuse of credentials or resources.',
          false: 'The pattern is consistent with a misconfiguration, capacity issue, or normal user error.',
        },
      },
    },
  })

  const { category, urgency, securityRelated } = result.answers
  const confidence = result.providerMetadata?.typesafe?.confidence as Record<string, number> | undefined
  const categoryConfidence = confidence?.category ?? 0
  const selectedProbability = category.probabilities?.[category.choice] ?? 0

  const decision =
    categoryConfidence < CONFIDENCE_FLOOR || selectedProbability < PROBABILITY_FLOOR
      ? { action: 'human-review', reason: 'ambiguous category' }
      : {
          action: 'route',
          queue: category.choice,
          urgency: urgency.score,
          notifySecurity: securityRelated.probability >= 0.8,
        }

  return { answers: result.answers, confidence, decision }
}

async function main() {
  const file = process.argv[2] ?? 'sample-alert.json'
  const alert = JSON.parse(readFileSync(file, 'utf8'))
  const started = Date.now()
  const outcome = await triage(alert)
  console.log('Elapsed ms:', Date.now() - started)
  console.log(JSON.stringify(outcome, null, 2))
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})