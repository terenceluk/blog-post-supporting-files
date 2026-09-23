import { experimental_evaluate as evaluate } from 'ai'

async function main() {
  const started = Date.now()

  const result = await evaluate({
    model: 'typesafe-ai/jev',
    state: {
      subject: 'Stripe sync broken',
      message:
        'Our Stripe connection has failed for three days and invoices are not being created. ' +
        'We have customers waiting on them. If this is not fixed today I want a credit for this month.',
      plan: 'pro',
      previousTickets: 2,
    },
    questions: {
      department: {
        type: 'choice',
        instructions: 'Which team should handle this ticket?',
        criteria: {
          billing: 'Charges, invoices, and refunds',
          technical: 'Bugs, outages, and integration failures',
          account: 'Login, permissions, and profile changes',
          other: 'Anything that does not fit the other teams',
        },
      },
      severity: {
        type: 'score',
        instructions: 'How severe is the issue for the customer?',
        criteria: [
          'Cosmetic or informational',
          'Degraded, but a workaround exists',
          'Blocking with no workaround',
          'Blocking and causing financial or data loss',
        ],
      },
      requestsRefund: {
        type: 'boolean',
        instructions: 'Is the customer asking for money back or a credit?',
        criteria: {
          true: 'The customer asks for a refund, credit, or reversal of a charge.',
          false: 'The customer does not ask for any money back.',
        },
      },
    },
  })

  console.log('Elapsed ms:', Date.now() - started)
  console.log('Answers:', JSON.stringify(result.answers, null, 2))
  console.log('Confidence:', JSON.stringify(result.providerMetadata?.typesafe?.confidence, null, 2))
  console.log('Usage:', JSON.stringify(result.usage))
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
