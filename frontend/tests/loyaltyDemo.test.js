import assert from 'node:assert/strict'
import test from 'node:test'

import {
  addDemoVisits,
  applyDemoBenefit,
  createLoyaltyDemo,
  cycleProgress,
} from '../src/utils/loyaltyDemo.js'

test('la demostración sigue ciclos de 6, 5, 4 y 4 ingresos', () => {
  let state = createLoyaltyDemo()

  for (const [target, milestone] of [[6, 6], [5, 11], [4, 15], [4, 19]]) {
    assert.equal(cycleProgress(state).target, target)
    state = addDemoVisits(state, target)
    assert.equal(cycleProgress(state).pending, true)
    state = applyDemoBenefit(state)
    assert.equal(state.lastMilestone, milestone)
    assert.equal(cycleProgress(state).visits, 0)
  }
  assert.deepEqual(state.history.map((entry) => entry.milestone), [6, 11, 15, 19])
})

test('no reinicia antes del beneficio y conserva ingresos adicionales', () => {
  let state = addDemoVisits(createLoyaltyDemo(), 5)
  assert.equal(applyDemoBenefit(state), state)

  state = addDemoVisits(state, 2)
  assert.deepEqual(cycleProgress(state), { target: 6, visits: 7, pending: true })
  state = applyDemoBenefit(state)
  assert.deepEqual(cycleProgress(state), { target: 5, visits: 1, pending: false })
  assert.equal(addDemoVisits(state, 0), state)
})
