export function createLoyaltyDemo() {
  return { totalVisits: 0, completedCycles: 0, lastMilestone: 0, history: [] }
}

export function cycleTarget(completedCycles) {
  return completedCycles === 0 ? 6 : completedCycles === 1 ? 5 : 4
}

export function cycleProgress(state) {
  const target = cycleTarget(state.completedCycles)
  const visits = state.totalVisits - state.lastMilestone
  return { target, visits, pending: visits >= target }
}

export function addDemoVisits(state, amount = 1) {
  if (!Number.isSafeInteger(amount) || amount < 1) return state
  return { ...state, totalVisits: state.totalVisits + amount }
}

export function applyDemoBenefit(state) {
  const progress = cycleProgress(state)
  if (!progress.pending) return state

  const milestone = state.lastMilestone + progress.target
  return {
    ...state,
    completedCycles: state.completedCycles + 1,
    lastMilestone: milestone,
    history: [
      ...state.history,
      { cycle: state.completedCycles + 1, target: progress.target, milestone },
    ],
  }
}
