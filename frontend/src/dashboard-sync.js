import { canOpenActivity } from './pathways.js'

function finiteNumber(value) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

export function resolveDashboardResponse(currentDashboard, incomingDashboard, requestId, latestRequestId) {
  if (requestId !== latestRequestId) return { dashboard: currentDashboard, accepted: false }
  return { dashboard: incomingDashboard, accepted: true }
}

// El detalle y la entrega devuelven la fila de gamificación calculada por
// Django. La usamos solo para corregir la fila ya recibida del dashboard;
// nunca construimos asignaciones ni permisos en el navegador.
export function mergeDashboardChallenge(dashboard, assignmentId, gamification, submission = null) {
  if (!dashboard || !Array.isArray(dashboard.assignments) || !assignmentId || typeof gamification?.completed !== 'boolean') return dashboard
  const id = String(assignmentId)
  let changed = false
  const assignments = dashboard.assignments.map((assignment) => {
    if (String(assignment?.id) !== id) return assignment
    changed = true
    const earnedXp = finiteNumber(gamification.earned_xp)
    const progress = finiteNumber(gamification.progress)
    const submissions = finiteNumber(assignment.submissions)
    const attemptNumber = finiteNumber(submission?.attempt_number)
    return {
      ...assignment,
      completed: gamification.completed,
      ...(earnedXp == null ? {} : { earned_xp: Math.max(0, earnedXp) }),
      ...(progress == null ? {} : { progress: Math.min(100, Math.max(0, progress)) }),
      ...(submission && submissions != null ? {
        // Una recarga de foco puede haber incorporado ya esta evidencia. El
        // número de intento del servidor evita contarla dos veces.
        submissions: Math.max(submissions, attemptNumber == null ? submissions : attemptNumber),
        status: assignment.status === 'graded' ? 'graded' : 'submitted',
      } : {}),
    }
  })
  return changed ? { ...dashboard, assignments } : dashboard
}

// `assignments` ya llega ordenado y limitado a la matrícula activa por Django.
// Recorremos esa lista sin reordenarla y omitimos cualquier fila bloqueada.
export function findNextAvailableActivity(assignments = [], currentAssignmentId, pathways = []) {
  const currentIndex = assignments.findIndex((assignment) => String(assignment?.id) === String(currentAssignmentId))
  if (currentIndex < 0) return null
  return assignments.slice(currentIndex + 1).find((assignment) => assignment?.completed !== true && canOpenActivity(assignment, pathways)) || null
}
