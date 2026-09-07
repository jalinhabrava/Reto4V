import test from 'node:test'
import assert from 'node:assert/strict'
import {
  canOpenActivity,
  filterActivities,
  isActivityLocked,
  normalizePathway,
  normalizePathways,
  pathwayForActivity,
  pathwayProgress,
  selectCurrentActivity,
} from '../src/pathways.js'

const assignments = [
  { id: 'html-1', language: 'web', pathway: 'html_css', completed: false },
  { id: 'html-2', language: 'web', pathway: 'html_css', completed: true },
  { id: 'js-1', language: 'web', pathway: 'javascript', locked: true, lock_reason: 'Completa HTML y CSS.' },
  { id: 'bash-1', language: 'bash' },
]

test('normaliza etapas web antiguas y conserva el idioma estático', () => {
  assert.equal(normalizePathway(undefined, 'web'), 'html_css')
  assert.equal(normalizePathway('javascript', 'web'), 'javascript')
  assert.equal(normalizePathway('desconocida', 'bash'), 'bash')
  assert.equal(pathwayForActivity({ version: { language: 'web', pathway: 'javascript' } }), 'javascript')
})

test('filtra etapas sin mezclar HTML/CSS con JavaScript', () => {
  assert.deepEqual(filterActivities(assignments, 'web', 'html_css').map(({ id }) => id), ['html-1', 'html-2'])
  assert.deepEqual(filterActivities(assignments, 'web', 'javascript').map(({ id }) => id), ['js-1'])
})

test('una actividad bloqueada no se puede abrir y nunca es la actual', () => {
  const pathways = normalizePathways([
    { id: 'html_css', total: 2, completed: 2 },
    { id: 'javascript', total: 1, completed: 0, locked: true, lock_reason: 'Requisito pendiente.' },
  ])
  assert.equal(isActivityLocked(assignments[2], pathways), true)
  assert.equal(canOpenActivity(assignments[2], pathways), false)
  assert.equal(selectCurrentActivity(assignments, 'web', 'javascript', pathways), null)
  assert.equal(selectCurrentActivity(assignments, 'web', 'html_css', pathways).id, 'html-1')
})

test('el override administrativo desbloquea la etapa JavaScript', () => {
  const pathways = normalizePathways([{ id: 'javascript', total: 1, completed: 0, locked: true, unlock_override: true }])
  const activity = { ...assignments[2], locked: false }
  assert.equal(isActivityLocked(activity, pathways), false)
  assert.equal(selectCurrentActivity([activity], 'web', 'javascript', pathways).id, 'js-1')
  assert.deepEqual(pathwayProgress(pathways, 'javascript'), { total: 1, completed: 0, locked: false, unlock_override: true, lock_reason: '' })
})
