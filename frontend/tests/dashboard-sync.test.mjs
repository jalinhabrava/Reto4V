import test from 'node:test'
import assert from 'node:assert/strict'
import { findNextAvailableActivity, mergeDashboardChallenge, resolveDashboardResponse } from '../src/dashboard-sync.js'

const pathways = [
  { id: 'html_css', total: 2, completed: 2, locked: false },
  { id: 'javascript', total: 1, completed: 0, locked: true },
]

const assignments = [
  { id: 'html-1', language: 'web', pathway: 'html_css', completed: true, submissions: 1, status: 'graded' },
  { id: 'html-2', language: 'web', pathway: 'html_css', completed: false, submissions: 0, status: 'not_started' },
  { id: 'js-1', language: 'web', pathway: 'javascript', completed: false },
]

test('reconcilia solo la fila confirmada por Django sin fabricar una asignación', () => {
  const dashboard = { assignments }
  const merged = mergeDashboardChallenge(dashboard, 'html-1', { completed: true, earned_xp: 80, progress: 100 }, { attempt_number: 1 })
  assert.notEqual(merged, dashboard)
  assert.equal(merged.assignments[0].completed, true)
  assert.equal(merged.assignments[0].earned_xp, 80)
  assert.equal(merged.assignments[0].submissions, 1)
  assert.equal(merged.assignments[0].status, 'graded')
  assert.equal(mergeDashboardChallenge(dashboard, 'missing', { completed: true }), dashboard)
})

test('el siguiente reto conserva el orden del servidor y nunca recomienda bloqueados', () => {
  assert.equal(findNextAvailableActivity(assignments, 'html-1', pathways).id, 'html-2')
  assert.equal(findNextAvailableActivity(assignments, 'html-2', pathways), null)
})

test('JavaScript aparece como siguiente solo cuando el snapshot nuevo lo desbloquea', () => {
  const completedHtml = assignments.map((assignment) => assignment.id === 'html-2' ? { ...assignment, completed: true } : assignment)
  assert.equal(findNextAvailableActivity(completedHtml, 'html-2', pathways), null)
  const unlocked = pathways.map((pathway) => pathway.id === 'javascript' ? { ...pathway, locked: false } : pathway)
  assert.equal(findNextAvailableActivity(completedHtml, 'html-2', unlocked).id, 'js-1')
})

test('una respuesta antigua no puede sustituir al snapshot más reciente', () => {
  const newer = { assignments: [{ id: 'html-1', completed: true }] }
  const stale = { assignments: [{ id: 'html-1', completed: false }] }
  assert.deepEqual(resolveDashboardResponse(newer, stale, 4, 5), { dashboard: newer, accepted: false })
  assert.deepEqual(resolveDashboardResponse(newer, stale, 5, 5), { dashboard: stale, accepted: true })
})
