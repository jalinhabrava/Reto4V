const WEB_PATHWAYS = new Set(['html_css', 'javascript'])

export const PATHWAY_LABELS = {
  html_css: 'HTML y CSS',
  javascript: 'JavaScript',
  web: 'Web',
  bash: 'Bash',
  python: 'Python',
}

export function normalizePathway(value, language = 'web') {
  const normalizedLanguage = String(language || 'web').toLowerCase()
  const normalized = String(value || '').toLowerCase()
  if (WEB_PATHWAYS.has(normalized)) return normalized
  if (normalizedLanguage === 'bash' || normalizedLanguage === 'python') return normalizedLanguage
  // Las actividades Web antiguas no tenían etapa: empiezan por HTML/CSS.
  return 'html_css'
}

export function pathwayForActivity(activity = {}) {
  const language = String(activity.language || activity.track || activity.version?.language || 'web').toLowerCase()
  return normalizePathway(activity.pathway ?? activity.version?.pathway, language)
}

export function normalizePathwaySummary(summary = {}) {
  const id = normalizePathway(summary.id || summary.pathway, summary.language || summary.id)
  const number = (value) => {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? Math.max(0, parsed) : 0
  }
  return {
    ...summary,
    id,
    title: String(summary.title || PATHWAY_LABELS[id] || id),
    total: number(summary.total),
    completed: number(summary.completed),
    locked: summary.locked === true,
    unlock_override: summary.unlock_override === true,
    lock_reason: typeof summary.lock_reason === 'string' ? summary.lock_reason : '',
  }
}

export function normalizePathways(value, activities = []) {
  const raw = Array.isArray(value) ? value : []
  const summaries = raw.filter(Boolean).map(normalizePathwaySummary)
  if (summaries.length) return summaries

  const webActivities = activities.filter((activity) => String(activity.language || activity.track || 'web').toLowerCase() === 'web')
  if (!webActivities.length) return []
  return ['html_css', 'javascript'].map((id) => {
    const pathwayActivities = webActivities.filter((activity) => pathwayForActivity(activity) === id)
    const completed = pathwayActivities.filter((activity) => activity.completed === true).length
    return normalizePathwaySummary({
      id,
      title: PATHWAY_LABELS[id],
      total: pathwayActivities.length,
      completed,
      locked: id === 'javascript' && pathwayActivities.length === 0,
      lock_reason: id === 'javascript' && pathwayActivities.length === 0 ? 'Completa HTML y CSS para desbloquear este recorrido.' : '',
    })
  })
}

export function getPathwaySummary(pathways, id) {
  return (Array.isArray(pathways) ? pathways : []).find((pathway) => normalizePathwaySummary(pathway).id === id) || null
}

export function isPathwayLocked(pathway) {
  const summary = normalizePathwaySummary(pathway || {})
  return summary.locked && !summary.unlock_override
}

export function isActivityLocked(activity = {}, pathways = []) {
  if (activity.locked === true) return true
  const pathway = pathwayForActivity(activity)
  const summary = getPathwaySummary(pathways, pathway)
  return Boolean(summary && isPathwayLocked(summary))
}

export function lockReasonForActivity(activity = {}, pathways = []) {
  if (typeof activity.lock_reason === 'string' && activity.lock_reason.trim()) return activity.lock_reason
  const summary = getPathwaySummary(pathways, pathwayForActivity(activity))
  return summary?.lock_reason || 'Este recorrido todavía está bloqueado.'
}

export function canOpenActivity(activity, pathways = []) {
  return Boolean(activity?.id) && !isActivityLocked(activity, pathways)
}

export function filterActivities(activities = [], track = 'all', pathway = 'all') {
  return activities.filter((activity) => {
    const language = String(activity.language || activity.track || activity.version?.language || 'web').toLowerCase()
    if (track !== 'all' && language !== track) return false
    return pathway === 'all' || pathwayForActivity(activity) === pathway
  })
}

export function selectCurrentActivity(activities = [], track = 'all', pathway = 'all', pathways = []) {
  const available = filterActivities(activities, track, pathway).filter((activity) => !isActivityLocked(activity, pathways))
  // La lista ya tiene el orden pedagógico del servidor. El CTA no debe saltar
  // un paso pendiente solo porque haya otro reto abierto o ya completado.
  return available.find((activity) => activity.completed !== true) || available[0] || null
}

export function pathwayProgress(pathways = [], id = 'html_css') {
  const summary = getPathwaySummary(pathways, id)
  return {
    total: summary?.total || 0,
    completed: summary?.completed || 0,
    locked: summary ? isPathwayLocked(summary) : false,
    unlock_override: summary?.unlock_override === true,
    lock_reason: summary?.lock_reason || '',
  }
}
