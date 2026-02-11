import { buildSystemStatus } from './systemStatusLogic'

function assert(condition: boolean, message: string) {
  if (!condition) throw new Error(message)
}

function test(name: string, runner: () => void) {
  try {
    runner()
    console.log(`PASS: ${name}`)
  } catch (error) {
    console.error(`FAIL: ${name}`)
    throw error
  }
}

test('mode unknown should be restricted with MODE_UNKNOWN as primary', () => {
  const result = buildSystemStatus({
    writeAccess: {
      canWrite: false,
      reason: 'MODE_UNKNOWN',
      mode: null,
    },
    contractWriteAllowed: true,
    contractMissingOperations: [],
    hasAdminToken: false,
    source: 'test',
  })

  assert(result.isRestricted === true, 'expected isRestricted=true when mode is unknown')
  assert(result.primary?.code === 'MODE_UNKNOWN', 'expected primary code MODE_UNKNOWN')
})

test('contract deny should have CONTRACT_OPERATION_UNAVAILABLE as primary', () => {
  const result = buildSystemStatus({
    writeAccess: {
      canWrite: false,
      reason: 'MODE_UNKNOWN',
      mode: null,
    },
    contractWriteAllowed: false,
    contractMissingOperations: ['POST /api/config/entries'],
    hasAdminToken: false,
    source: 'test',
  })

  assert(
    result.primary?.code === 'CONTRACT_OPERATION_UNAVAILABLE',
    'expected CONTRACT_OPERATION_UNAVAILABLE to be selected as primary'
  )
})
