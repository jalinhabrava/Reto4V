import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { EditorState } from '@codemirror/state'
import { defaultKeymap, history, historyKeymap, indentWithTab, redo, undo } from '@codemirror/commands'
import { html } from '@codemirror/lang-html'
import { css } from '@codemirror/lang-css'
import { javascript } from '@codemirror/lang-javascript'
import { defaultHighlightStyle, indentOnInput, StreamLanguage, syntaxHighlighting } from '@codemirror/language'
import { autocompletion } from '@codemirror/autocomplete'
import { bracketMatching } from '@codemirror/language'
import { lineNumbers, EditorView, drawSelection, highlightActiveLine, keymap } from '@codemirror/view'
import { oneDark } from '@codemirror/theme-one-dark'
import {
  IconAlertTriangle,
  IconArrowLeft,
  IconArrowRight,
  IconBrandCss3,
  IconBrandHtml5,
  IconBrandJavascript,
  IconBrowser,
  IconCalendarEvent,
  IconChartBar,
  IconCheck,
  IconChevronDown,
  IconChevronRight,
  IconCircleCheck,
  IconCircleX,
  IconClock,
  IconCode,
  IconDeviceFloppy,
  IconFileCode,
  IconHistory,
  IconHome2,
  IconInfoCircle,
  IconLayoutDashboard,
  IconListCheck,
  IconLogout,
  IconMenu2,
  IconPlayerPlay,
  IconRefresh,
  IconRocket,
  IconSchool,
  IconSettings,
  IconTerminal2,
  IconTestPipe,
  IconUser,
  IconUsers,
  IconX,
} from '@tabler/icons-react'
import './styles.css'

const API_PREFIX = '/api'
const PREVIEW_NONCE = document.querySelector('meta[name="reto4v-preview-nonce"], meta[name="aulaweb-preview-nonce"]')?.content || ''
// La demo solo existe durante `vite dev`; un build de producción no fabrica
// sesiones, notas, entregas ni actividades si el backend no responde.
const DEMO_MODE = import.meta.env.DEV

const FILES_DEFAULT = {
  html: '<main class="card">\n  <span class="eyebrow">SMR · CSS</span>\n  <h1>Mi tarjeta</h1>\n  <p>Añade los estilos para completar el reto.</p>\n  <button id="action">Probar interacción</button>\n</main>',
  css: ':root {\n  color-scheme: light;\n  font-family: system-ui, sans-serif;\n}\n\nbody {\n  margin: 0;\n  min-height: 100vh;\n  display: grid;\n  place-items: center;\n  background: #e9eef2;\n}\n\n.card {\n  width: min(360px, calc(100vw - 40px));\n  padding: 32px;\n  border-radius: 20px;\n  background: white;\n  box-shadow: 0 20px 50px rgb(13 34 56 / 12%);\n}',
  javascript: "const action = document.querySelector('#action');\n\naction?.addEventListener('click', () => {\n  console.log('¡Funciona!');\n});",
}

const BASH_FILES_DEFAULT = {
  bash: `#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="./backups"
SOURCE_DIR="./datos"
STAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$BACKUP_DIR"
tar -czf "$BACKUP_DIR/datos-$STAMP.tar.gz" "$SOURCE_DIR"
echo "Copia preparada: $BACKUP_DIR/datos-$STAMP.tar.gz"`,
}

const DEMO_USER_STUDENT = {
  id: 'demo-student',
  username: 'lucia.garcia',
  display_name: 'Lucía García',
  role: 'student',
  group: '1SMR-A · Web + scripting',
}

const DEMO_USER_TEACHER = {
  id: 'demo-teacher',
  username: 'javier.martin',
  display_name: 'Javier Martín',
  role: 'teacher',
  group: '1SMR-A · Web / 2ASIR · Seguridad',
}

const DEMO_ACTIVITIES = [
  {
    id: 'box-model',
    title: 'Modelo de caja con CSS',
    module: 'CSS · Unidad 02',
    summary: 'Da forma, espacio y jerarquía a una tarjeta de perfil.',
    status: 'in_progress',
    progress: 62,
    due: 'Hoy, 23:59',
    difficulty: 'Inicial',
    points: 10,
    tests: 4,
    attempts: 2,
    revision: 3,
    language: 'web',
    difficulty: 'beginner',
    xp_reward: 70,
    earned_xp: 48,
    completed: false,
  },
  {
    id: 'semantic-html',
    title: 'Estructura semántica',
    module: 'HTML · Unidad 01',
    summary: 'Ordena una página con landmarks y contenido accesible.',
    status: 'graded',
    progress: 100,
    due: 'Entregada ayer',
    difficulty: 'Inicial',
    points: 10,
    score: 9.2,
    tests: 5,
    attempts: 1,
    revision: 2,
    language: 'web',
    difficulty: 'beginner',
    xp_reward: 60,
    earned_xp: 60,
    completed: true,
  },
  {
    id: 'dom-events',
    title: 'Eventos y DOM',
    module: 'JavaScript · Unidad 03',
    summary: 'Conecta acciones del usuario con una interfaz que responde.',
    status: 'not_started',
    progress: 0,
    due: 'Viernes, 23:59',
    difficulty: 'intermediate',
    points: 10,
    tests: 6,
    attempts: 3,
    revision: 1,
    language: 'web',
    difficulty: 'beginner',
    xp_reward: 60,
    earned_xp: 36,
    completed: false,
  },
  {
    id: 'bash-backup',
    title: 'Copia segura con Bash',
    module: 'Seguridad · Unidad 02',
    summary: 'Construye un script reproducible para empaquetar y verificar una copia.',
    status: 'in_progress',
    progress: 45,
    due: 'Miércoles, 23:59',
    difficulty: 'intermediate',
    points: 10,
    tests: 5,
    attempts: 1,
    revision: 2,
    language: 'bash',
    track: 'bash',
    xp_reward: 90,
    earned_xp: 40,
    completed: false,
  },
  {
    id: 'bash-permissions',
    title: 'Permisos y evidencias',
    module: 'Seguridad · Unidad 03',
    summary: 'Detecta permisos inseguros y deja un registro útil para auditoría.',
    status: 'not_started',
    progress: 0,
    due: 'Viernes, 23:59',
    difficulty: 'advanced',
    points: 10,
    tests: 4,
    attempts: 0,
    revision: 1,
    language: 'bash',
    track: 'bash',
    xp_reward: 120,
    earned_xp: 0,
    completed: false,
  },
]

const DEMO_TEACHER_ROWS = [
  { name: 'Lucía García', initials: 'LG', semantic: 9.2, box: 'En curso', dom: '—', recent: 'hace 12 min', tone: 'mint' },
  { name: 'Álvaro Nieto', initials: 'AN', semantic: 7.8, box: 6.5, dom: 'Pendiente', recent: 'hace 31 min', tone: 'amber' },
  { name: 'Nerea Soler', initials: 'NS', semantic: 10, box: 8.8, dom: '—', recent: 'ayer', tone: 'violet' },
  { name: 'Pablo Ruiz', initials: 'PR', semantic: 'Pendiente', box: 'No iniciado', dom: '—', recent: 'hace 3 días', tone: 'blue' },
  { name: 'Irene Castro', initials: 'IC', semantic: 8.6, box: 'En curso', dom: '—', recent: 'hace 1 h', tone: 'peach' },
]

const DEMO_TESTS = [
  { id: 'html-main', title: 'Existe un elemento <main>', description: 'La página contiene un único landmark principal.', points: 2, status: 'passed', feedback: 'Buen punto de entrada semántico.' },
  { id: 'css-radius', title: 'La tarjeta tiene esquinas suaves', description: 'Usa border-radius para separar la tarjeta del fondo.', points: 2, status: 'passed', feedback: 'La propiedad está presente.' },
  { id: 'css-spacing', title: 'La tarjeta respira', description: 'El contenido tiene padding suficiente.', points: 3, status: 'failed', feedback: 'Prueba con un padding de 24px o más.' },
  { id: 'js-console', title: 'El botón responde', description: 'Al hacer clic se registra un mensaje en la consola.', points: 3, status: 'pending', feedback: 'Ejecuta la preview y prueba el botón.' },
]

const DEMO_BASH_TESTS = [
  { id: 'bash-shebang', title: 'Declara Bash explícitamente', description: 'El script empieza con un shebang portable para Bash.', points: 2, status: 'passed', feedback: 'El intérprete está declarado.' },
  { id: 'bash-safe-mode', title: 'Activa el modo seguro', description: 'Incluye opciones para detener errores y variables no definidas.', points: 2, status: 'pending', feedback: 'Añade set -euo pipefail al principio.' },
  { id: 'bash-archive', title: 'Genera un archivo comprimido', description: 'Usa una herramienta de archivado con una ruta de salida clara.', points: 3, status: 'pending', feedback: 'Comprueba la salida de tar y el destino.' },
  { id: 'bash-quoting', title: 'Protege las rutas', description: 'Las rutas construidas con variables aparecen entre comillas.', points: 2, status: 'pending', feedback: 'Revisa el uso de comillas dobles.' },
  { id: 'bash-exit', title: 'Comunica el resultado', description: 'El script deja un mensaje o código de salida comprensible.', points: 1, status: 'pending', feedback: 'Incluye una salida útil para quien lo ejecute.' },
]

const DEMO_GAMIFICATION = {
  total_xp: 420,
  level: 1,
  level_progress: 84,
  xp_to_next_level: 80,
  completed_challenges: 7,
  badges: [
    { id: 'first-script', title: 'Primer script', description: 'Has completado tu primer reto de código.' },
    { id: 'steady-hand', title: 'Pulso constante', description: 'Has superado retos de dos itinerarios.' },
    { id: 'backup-ready', title: 'Backup listo', description: 'Has trabajado con copias reproducibles.' },
  ],
}

const FILE_META = {
  html: { label: 'index.html', short: 'HTML', icon: IconBrandHtml5, className: 'file-html' },
  css: { label: 'styles.css', short: 'CSS', icon: IconBrandCss3, className: 'file-css' },
  javascript: { label: 'script.js', short: 'JS', icon: IconBrandJavascript, className: 'file-js' },
}

function readBootstrap() {
  const parseNode = (node) => {
    if (!node?.textContent) return null
    try { return JSON.parse(node.textContent) } catch { return null }
  }
  const bootstrap = parseNode(document.getElementById('aulaweb-bootstrap'))
  const workspace = parseNode(document.getElementById('workspace-data'))
  const userPayload = parseNode(document.getElementById('user-data'))
  if (bootstrap) return bootstrap
  if (workspace) return { ...workspace, user: userPayload }
  if (userPayload) return { user: userPayload }
  return null
}

function getCookie(name) {
  const prefix = `${name}=`
  const match = document.cookie.split(';').map((cookie) => cookie.trim()).find((cookie) => cookie.startsWith(prefix))
  return match ? decodeURIComponent(match.slice(prefix.length)) : ''
}

async function apiFetch(path, options = {}) {
  const method = (options.method || 'GET').toUpperCase()
  const headers = { Accept: 'application/json', ...(options.headers || {}) }
  if (options.body && !headers['Content-Type']) headers['Content-Type'] = 'application/json'
  if (method !== 'GET' && method !== 'HEAD') headers['X-CSRFToken'] = getCookie('csrftoken')
  const response = await fetch(path, { credentials: 'same-origin', ...options, method, headers })
  const text = await response.text()
  let payload = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = { detail: text }
    }
  }
  if (!response.ok) {
    const error = new Error(payload?.detail || payload?.message || `Error ${response.status}`)
    error.status = response.status
    error.payload = payload
    throw error
  }
  return payload
}

function Icon({ icon: IconComponent, size = 18, stroke = 1.8, ...props }) {
  return <IconComponent size={size} stroke={stroke} aria-hidden="true" {...props} />
}

function normalizeUser(user) {
  if (!user) return null
  return { ...user, group: user.group || user.groups?.join(' · ') || '' }
}

const TRACKS = {
  all: { label: 'Todos los retos', shortLabel: 'Todo', description: 'Tu recorrido completo' },
  web: { label: 'Web · SMR', shortLabel: 'Web · SMR', description: 'HTML, CSS y JavaScript' },
  bash: { label: 'Bash · ASIR', shortLabel: 'Bash · ASIR', description: 'Linux, scripting y seguridad' },
}

function normalizeLanguage(value) {
  return String(value || 'web').toLowerCase() === 'bash' ? 'bash' : 'web'
}

function trackForActivity(activity) {
  return normalizeLanguage(activity?.language || activity?.track || activity?.version?.language)
}

function normalizeGamification(source) {
  const raw = source?.gamification || source?.dashboard?.gamification || {}
  const number = (value, fallback = 0) => {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : fallback
  }
  return {
    total_xp: Math.max(0, number(raw.total_xp ?? raw.totalXp)),
    level: Math.max(1, number(raw.level, 1)),
    level_progress: Math.min(100, Math.max(0, number(raw.level_progress ?? raw.levelProgress))),
    xp_to_next_level: Math.max(0, number(raw.xp_to_next_level ?? raw.xpToNextLevel)),
    completed_challenges: Math.max(0, number(raw.completed_challenges ?? raw.completedChallenges)),
    badges: Array.isArray(raw.badges) ? raw.badges.filter(Boolean).map((badge) => ({
      id: String(badge.id || badge.slug || badge.title || 'badge'),
      title: String(badge.title || badge.name || 'Insignia'),
      description: String(badge.description || badge.detail || ''),
    })) : [],
  }
}

function normalizeChallengeGamification(source, activity = {}) {
  const raw = source?.gamification || source || {}
  const number = (value, fallback = 0) => {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : fallback
  }
  const reward = number(raw.xp_reward ?? activity.xp_reward)
  const earned = number(raw.earned_xp ?? activity.earned_xp)
  return {
    assignment_id: raw.assignment_id || activity.id || null,
    language: normalizeLanguage(raw.language || activity.language),
    difficulty: raw.difficulty || activity.difficulty || 'beginner',
    xp_reward: Math.max(0, reward),
    earned_xp: Math.max(0, earned),
    best_score: raw.best_score == null ? null : number(raw.best_score),
    completed: typeof raw.completed === 'boolean' ? raw.completed : typeof activity.completed === 'boolean' ? activity.completed : false,
    progress: Math.min(100, Math.max(0, number(raw.progress ?? activity.progress))),
  }
}

function getDifficultyLabel(value) {
  const normalized = String(value || '').toLowerCase()
  return { beginner: 'Inicial', intermediate: 'Intermedio', advanced: 'Avanzado' }[normalized] || value || 'Reto'
}

function assignmentWithDefaults(assignment) {
  const language = normalizeLanguage(assignment?.language || assignment?.track)
  const earned = Number(assignment?.earned_xp)
  const reward = Number(assignment?.xp_reward)
  return {
    ...assignment,
    language,
    module: assignment?.module || (language === 'bash' ? 'Seguridad · Linux' : 'Aplicaciones web · SMR'),
    summary: assignment?.summary || (language === 'bash' ? 'Practica scripting de Linux y comprueba tus decisiones.' : 'Practica y entrega esta actividad desde el editor.'),
    difficulty: assignment?.difficulty || 'beginner',
    xp_reward: Number.isFinite(reward) ? reward : 0,
    earned_xp: Number.isFinite(earned) ? earned : 0,
    progress: assignment?.progress != null && Number.isFinite(Number(assignment.progress)) ? Math.min(100, Math.max(0, Number(assignment.progress))) : assignment?.completed ? 100 : null,
    // El backend decide cuándo un reto cuenta como dominio (no confundimos
    // una entrega académica publicada con una insignia conseguida).
    completed: typeof assignment?.completed === 'boolean' ? assignment.completed : false,
  }
}

const CLIENT_SECONDARY_VIEWS = new Set(['activities'])

function readClientRoute() {
  const pathname = window.location.pathname.replace(/\/+$/, '') || '/'
  const assignmentMatch = pathname.match(/^\/(?:student\/)?assignments\/([^/]+)$/)
  if (assignmentMatch) {
    let assignmentId = assignmentMatch[1]
    try { assignmentId = decodeURIComponent(assignmentId) } catch { /* La ruta sigue siendo válida aunque el id esté codificado de forma extraña. */ }
    return { view: 'workspace', assignmentId }
  }
  const hashView = window.location.hash.replace(/^#/, '')
  return { view: CLIENT_SECONDARY_VIEWS.has(hashView) ? hashView : 'dashboard' }
}

function dashboardPathFor(isTeacher) {
  return isTeacher ? '/teacher/dashboard/' : '/student/dashboard/'
}

function assignmentPathFor(assignmentId) {
  return `/assignments/${encodeURIComponent(String(assignmentId))}/`
}

function workspaceActivityFromPayload(payload, assignmentId) {
  const version = payload?.version || {}
  const activity = payload?.activity || {}
  return assignmentWithDefaults({
    id: payload?.id || assignmentId,
    title: payload?.title || activity.title || 'Reto de programación',
    module: activity.module,
    summary: version.instructions,
    instructions: version.instructions,
    objectives: version.objectives,
    hints: version.hints,
    language: version.language,
    difficulty: version.difficulty,
    xp_reward: version.xp_reward,
    status: payload?.status,
    max_attempts: payload?.max_attempts,
    attempts: payload?.max_attempts,
    curriculum_scope: version.curriculum_scope,
  })
}

function App() {
  const bootstrap = useMemo(() => readBootstrap(), [])
  const bootstrappedWorkspace = bootstrap?.workspace || (bootstrap?.activity && bootstrap?.version ? bootstrap : null)
  const [session, setSession] = useState(() => {
    if (bootstrap?.user) return normalizeUser(bootstrap.user)
    return null
  })

  const handleLogin = useCallback((user) => {
    const nextUser = DEMO_MODE ? { ...normalizeUser(user), demo: true } : normalizeUser(user)
    setSession(nextUser)
  }, [])

  const handleLogout = useCallback(async () => {
    try {
      await apiFetch('/logout/', { method: 'POST', body: '' })
    } catch {
      // El logout local también es válido cuando se abre el modo demo sin backend.
    }
    setSession(null)
  }, [])

  if (!session) return <LoginScreen onLogin={handleLogin} />
  return <AppShell user={session} onLogout={handleLogout} initialActivity={bootstrappedWorkspace} initialView={bootstrappedWorkspace ? 'workspace' : 'dashboard'} initialDashboard={bootstrap?.dashboard || null} />
}

function LoginScreen({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const response = await fetch('/login/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { Accept: 'text/html', 'X-CSRFToken': getCookie('csrftoken'), 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8' },
        body: new URLSearchParams({ username, password }),
      })
      if (response.redirected && !response.url.includes('/login')) {
        window.location.assign(response.url)
        return
      }
      if (DEMO_MODE && username && password === 'demo') {
        onLogin(username.toLowerCase().includes('profe') || username.toLowerCase().includes('javier') ? DEMO_USER_TEACHER : DEMO_USER_STUDENT)
      } else {
        setError(response.status === 429 ? 'Demasiados intentos. Espera cinco minutos antes de volver a probar.' : response.status >= 500 ? 'No se pudo conectar con Reto4V.' : 'Usuario o contraseña incorrectos.')
      }
    } catch {
      if (DEMO_MODE && username && password === 'demo') onLogin(username.toLowerCase().includes('profe') || username.toLowerCase().includes('javier') ? DEMO_USER_TEACHER : DEMO_USER_STUDENT)
      else setError('No se pudo conectar con Reto4V.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="login-page">
      <section className="login-visual" aria-label="Reto4V para aprender programación">
        <div className="login-visual-inner">
          <a className="brand brand-light" href="/" aria-label="Reto4V, inicio">
            <img src="/static/brand-mark.svg" alt="" width="42" height="42" />
            <span>Reto4V<span className="brand-dot">.</span></span>
          </a>
          <div className="visual-copy">
            <p className="kicker kicker-light">Laboratorio de retos · 4 Vientos</p>
            <h1>Aprender haciendo<br /><em>se queda.</em></h1>
            <p className="visual-lede">Retos de programación para practicar web en SMR y scripting de Linux en ASIR, con feedback y progreso visible.</p>
          </div>
          <div className="visual-footer">
            <span className="pulse-dot" />
            <span>Servidor del centro · Solo LAN</span>
            <span className="footer-separator">/</span>
            <span>Sin datos externos</span>
          </div>
        </div>
        <div className="visual-grid" aria-hidden="true" />
        <div className="visual-orbit orbit-one" aria-hidden="true" />
        <div className="visual-orbit orbit-two" aria-hidden="true" />
      </section>

      <section className="login-panel">
        <div className="login-panel-inner">
          <div className="login-mobile-brand brand">
            <img src="/static/brand-mark.svg" alt="" width="38" height="38" />
            <span>Reto4V<span className="brand-dot">.</span></span>
          </div>
          <div className="login-intro">
            <p className="kicker">Bienvenido de nuevo</p>
            <h2>Entra a tu espacio.</h2>
            <p>Elige tu recorrido: web para SMR o Bash para seguridad y scripting en ASIR.</p>
          </div>
          <form className="login-form" onSubmit={submit}>
            <label htmlFor="username">Usuario</label>
            <div className="input-wrap">
              <Icon icon={IconUser} size={18} />
              <input id="username" name="username" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} placeholder="ej. alu001" required />
            </div>
            <label htmlFor="password">Contraseña</label>
            <div className="input-wrap">
              <Icon icon={IconCode} size={18} />
              <input id="password" name="password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Tu contraseña" required />
            </div>
            {error && <div className="form-error" role="alert"><Icon icon={IconAlertTriangle} size={17} />{error}</div>}
            <button className="button button-primary button-wide" type="submit" disabled={busy}>
              {busy ? <span className="button-loader" /> : <Icon icon={IconArrowRight} size={18} />}
              {busy ? 'Comprobando…' : 'Entrar en Reto4V'}
            </button>
          </form>
          {DEMO_MODE && <div className="demo-login">
            <span>¿Quieres ver la interfaz?</span>
            <div className="demo-actions">
              <button type="button" className="text-button" onClick={() => onLogin(DEMO_USER_STUDENT)}>Vista de alumno <Icon icon={IconArrowRight} size={15} /></button>
              <button type="button" className="text-button" onClick={() => onLogin(DEMO_USER_TEACHER)}>Vista de profesor <Icon icon={IconArrowRight} size={15} /></button>
            </div>
          </div>}
          <p className="login-note"><Icon icon={IconShieldIcon} size={15} />Tus datos viven únicamente en el servidor del instituto.</p>
        </div>
      </section>
    </main>
  )
}

function IconShieldIcon(props) {
  return <IconSchool {...props} />
}

function AppShell({ user, onLogout, initialActivity, initialView = 'dashboard', initialDashboard = null }) {
  const isTeacher = user.role === 'teacher' || user.role === 'admin'
  const initialRoute = useMemo(() => readClientRoute(), [])
  const initialRouteActivity = initialRoute.view === 'workspace' && initialRoute.assignmentId
    ? { id: initialRoute.assignmentId, title: 'Cargando reto…', language: 'web', difficulty: 'beginner' }
    : null
  const [view, setView] = useState(() => initialRoute.view === 'workspace' ? 'workspace' : initialView === 'workspace' ? 'workspace' : initialRoute.view)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [selectedActivity, setSelectedActivity] = useState(initialActivity || initialRouteActivity || (DEMO_MODE ? DEMO_ACTIVITIES[0] : null))
  const [dashboardData, setDashboardData] = useState(initialDashboard)
  const [dashboardRefreshToken, setDashboardRefreshToken] = useState(0)
  const [routeError, setRouteError] = useState('')
  const routeRequestRef = useRef(0)
  const activityCount = dashboardData?.assignments?.length ?? (DEMO_MODE ? DEMO_ACTIVITIES.length : 0)
  const contextGroup = user.group || (isTeacher ? 'Grupos asignados' : 'Mi grupo')
  const contextMark = contextGroup.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join('').toUpperCase() || 'AW'

  useEffect(() => {
    if (DEMO_MODE || view !== 'dashboard') return undefined
    let active = true
    const path = isTeacher ? '/teacher/dashboard/' : `${API_PREFIX}/student/dashboard/`
    apiFetch(path).then((data) => { if (active) setDashboardData(data) }).catch(() => { if (active) setDashboardData({ assignments: [], gamification: normalizeGamification({}) }) })
    return () => { active = false }
  }, [isTeacher, view, dashboardRefreshToken])

  useEffect(() => {
    const handlePopState = () => {
      const nextRoute = readClientRoute()
      setSidebarOpen(false)
      setRouteError('')
      setView(nextRoute.view)
      if (nextRoute.view !== 'workspace' || !nextRoute.assignmentId) {
        // Al volver del editor pedimos de nuevo el dashboard para reflejar
        // XP, progreso y entregas recién guardadas.
        setDashboardRefreshToken((current) => current + 1)
        return
      }

      const assignmentId = String(nextRoute.assignmentId)
      const knownAssignment = (dashboardData?.assignments || []).find((assignment) => String(assignment.id) === assignmentId)
      if (knownAssignment) {
        setSelectedActivity(assignmentWithDefaults(knownAssignment))
        return
      }
      if (initialActivity && String(initialActivity.id) === assignmentId) {
        setSelectedActivity(initialActivity)
        return
      }

      const requestId = ++routeRequestRef.current
      setSelectedActivity({ id: assignmentId, title: 'Cargando reto…', language: 'web', difficulty: 'beginner' })
      apiFetch(`${API_PREFIX}/assignments/${encodeURIComponent(assignmentId)}/`).then((data) => {
        if (requestId !== routeRequestRef.current || readClientRoute().assignmentId !== assignmentId) return
        setSelectedActivity(workspaceActivityFromPayload(data, assignmentId))
      }).catch(() => {
        if (requestId !== routeRequestRef.current) return
        setRouteError('No se pudo cargar ese reto. Hemos vuelto al resumen.')
        setView('dashboard')
        window.history.replaceState({ reto4vRoute: 'dashboard' }, '', dashboardPathFor(isTeacher))
        setDashboardRefreshToken((current) => current + 1)
      })
    }
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [dashboardData, initialActivity, isTeacher])

  const navigate = (nextView) => {
    const nextPath = nextView === 'dashboard' ? dashboardPathFor(isTeacher) : `${dashboardPathFor(isTeacher)}#${nextView}`
    const currentPath = `${window.location.pathname}${window.location.hash}`
    if (currentPath !== nextPath) window.history.pushState({ reto4vRoute: nextView }, '', nextPath)
    setView(nextView)
    setSidebarOpen(false)
    setRouteError('')
    if (nextView === 'dashboard') setDashboardRefreshToken((current) => current + 1)
  }

  const openActivity = (activity = null) => {
    if (!activity) return
    const assignmentId = String(activity.id)
    window.history.pushState({ reto4vRoute: 'workspace', assignmentId, fromPath: `${window.location.pathname}${window.location.hash}` }, '', assignmentPathFor(assignmentId))
    setSelectedActivity(activity)
    setView('workspace')
    setSidebarOpen(false)
    setRouteError('')
  }

  const workspaceOpen = view === 'workspace' && selectedActivity

  return (
    <div className={`app-shell ${workspaceOpen ? 'app-shell-workspace' : ''}`}>
      <button className={`mobile-overlay ${sidebarOpen ? 'is-visible' : ''}`} aria-label="Cerrar navegación" onClick={() => setSidebarOpen(false)} />
      <aside className={`app-sidebar ${sidebarOpen ? 'is-open' : ''}`}>
        <div className="sidebar-top">
          <a className="brand" href="#dashboard" onClick={(event) => { event.preventDefault(); navigate('dashboard') }}>
            <img src="/static/brand-mark.svg" alt="" width="36" height="36" />
            <span>Reto4V<span className="brand-dot">.</span></span>
          </a>
          <button type="button" className="icon-button sidebar-close" aria-label="Cerrar menú" onClick={() => setSidebarOpen(false)}><Icon icon={IconX} /></button>
        </div>
        <div className="sidebar-context">
          <span className="context-label">Aula actual</span>
          <div className="context-switcher"><span className="context-mark">{contextMark}</span><span>{contextGroup}</span></div>
        </div>
        <nav className="sidebar-nav" aria-label="Navegación principal">
          <span className="nav-section-label">Espacio de trabajo</span>
          <button className={`nav-item ${view === 'dashboard' ? 'is-active' : ''}`} onClick={() => navigate('dashboard')}><Icon icon={IconLayoutDashboard} /><span>Resumen</span></button>
          {!isTeacher && <button className={`nav-item ${view === 'activities' ? 'is-active' : ''}`} onClick={() => navigate('activities')}><Icon icon={IconCode} /><span>Mis retos</span><span className="nav-count">{activityCount || ''}</span></button>}
          {isTeacher && <a className="nav-item" href="/teacher/exports/?format=wide"><Icon icon={IconChartBar} /><span>Exportar calificaciones</span></a>}
          {user.role === 'admin' && <button className="nav-item" onClick={() => window.location.assign('/admin-ui/users/')}><Icon icon={IconUsers} /><span>Usuarios</span></button>}
        </nav>
        <div className="sidebar-bottom">
          <div className="server-status"><span className="pulse-dot pulse-dot-dark" /><span>Servidor local operativo</span></div>
          <a className="nav-item" href="/password-change/"><Icon icon={IconSettings} /><span>Preferencias</span></a>
          <button className="user-mini" type="button" onClick={onLogout} title="Cerrar sesión">
            <span className={`avatar avatar-${isTeacher ? 'teacher' : 'student'}`}>{getInitials(user.display_name)}</span>
            <span className="user-mini-copy"><strong>{user.display_name}</strong><small>{isTeacher ? 'Profesorado' : user.group || 'Alumno'}</small></span>
            <Icon icon={IconLogout} size={16} />
          </button>
        </div>
      </aside>
      <main className="app-main">
        {!workspaceOpen && <header className="mobile-header">
          <button type="button" className="icon-button" aria-label="Abrir menú" onClick={() => setSidebarOpen(true)}><Icon icon={IconMenu2} /></button>
          <a className="brand" href="#dashboard" onClick={(event) => { event.preventDefault(); navigate('dashboard') }}><img src="/static/brand-mark.svg" alt="" width="32" height="32" /><span>Reto4V<span className="brand-dot">.</span></span></a>
          <button type="button" className="avatar avatar-small" onClick={onLogout} aria-label="Cerrar sesión">{getInitials(user.display_name)}</button>
        </header>}
        {routeError && !workspaceOpen && <div className="route-error" role="alert"><Icon icon={IconAlertTriangle} size={15} />{routeError}</div>}
        {workspaceOpen ? <WorkspaceShell key={String(selectedActivity.id)} user={user} activity={selectedActivity} onBack={() => navigate('dashboard')} onLogout={onLogout} /> : view === 'dashboard' ? (isTeacher ? <TeacherDashboard user={user} data={dashboardData} onOpenActivity={openActivity} /> : <StudentDashboard user={user} data={dashboardData} onOpenActivity={openActivity} />) : <SecondaryView view={view} isTeacher={isTeacher} data={dashboardData} onOpenActivity={openActivity} />}
      </main>
    </div>
  )
}

function IconBookIcon(props) {
  return <IconBook2 {...props} />
}

function getInitials(name = '') {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join('').toUpperCase() || 'AW'
}

function DashboardHeader({ eyebrow, title, subtitle, action, onAction }) {
  return (
    <header className="dashboard-header">
      <div>
        <p className="kicker">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="dashboard-subtitle">{subtitle}</p>
      </div>
      {action && <button className="button button-dark" onClick={onAction}><Icon icon={action.icon} size={17} />{action.label}</button>}
    </header>
  )
}

function StudentDashboard({ user, data, onOpenActivity }) {
  const firstName = user.display_name?.split(' ')[0] || 'alumno'
  const sourceAssignments = Array.isArray(data?.assignments) ? data.assignments : (DEMO_MODE ? DEMO_ACTIVITIES : [])
  const activities = sourceAssignments.map(assignmentWithDefaults)
  const gamification = normalizeGamification(data || (DEMO_MODE ? { gamification: DEMO_GAMIFICATION } : null))
  const [activeTrack, setActiveTrack] = useState('all')
  const [tipIndex, setTipIndex] = useState(0)
  const filteredActivities = activeTrack === 'all' ? activities : activities.filter((activity) => trackForActivity(activity) === activeTrack)
  const currentActivity = filteredActivities[0] || {}
  const currentStatus = getStudentStatus(currentActivity.status)
  const measuredProgress = currentActivity.progress != null && Number.isFinite(Number(currentActivity.progress)) ? Number(currentActivity.progress) : null
  return (
    <div className="dashboard-page student-page">
      <DashboardHeader eyebrow={`Mi espacio · ${user.group || 'Reto4V'}`} title={`Hola, ${firstName}.`} subtitle={activities.length ? 'Elige un reto y convierte la práctica en progreso.' : 'Todavía no tienes retos asignados.'} action={filteredActivities.length ? { label: 'Abrir reto', icon: IconArrowRight } : null} onAction={() => onOpenActivity(currentActivity)} />
      <section className="track-switcher" aria-label="Filtrar itinerario">
        <div className="track-switcher-copy"><span className="card-overline">Tus itinerarios</span><strong>Practica por módulo</strong><small>Elige el contexto que quieres trabajar hoy.</small></div>
        <div className="track-options" role="group" aria-label="Itinerarios disponibles">
          {Object.entries(TRACKS).map(([key, track]) => <button key={key} className={`track-option ${activeTrack === key ? 'is-active' : ''}`} type="button" aria-pressed={activeTrack === key} onClick={() => setActiveTrack(key)}><span className={`track-option-mark track-mark-${key}`}><Icon icon={key === 'bash' ? IconTerminal2 : key === 'web' ? IconCode : IconLayoutDashboard} size={16} /></span><span><strong>{track.label}</strong><small>{track.description}</small></span><span className="track-option-count">{key === 'all' ? activities.length : activities.filter((activity) => trackForActivity(activity) === key).length}</span></button>)}
        </div>
      </section>
      <section className="student-overview-grid" aria-label="Resumen de aprendizaje">
        <div className="continue-card">
          <div className="continue-card-top">
            <span className="soft-pill pill-gold"><Icon icon={trackForActivity(currentActivity) === 'bash' ? IconTerminal2 : IconPlayerPlay} size={13} />{currentActivity.status ? currentStatus.label : 'Sin reto'}</span>
            <span className="continue-due"><Icon icon={IconClock} size={14} />{currentActivity.due_at ? formatDate(currentActivity.due_at) : currentActivity.due || 'Sin fecha'}</span>
          </div>
          <div className="continue-copy">
            <p className="card-overline">{currentActivity.module || 'Reto disponible'}</p>
            <h2>{currentActivity.title || 'Sin actividad'}<br /><em>{currentActivity.status ? currentStatus.label.toLowerCase() : 'pendiente'}</em></h2>
            <p>{currentActivity.summary || 'Cuando tu profesor publique un reto aparecerá aquí.'}</p>
          </div>
          <div className="continue-progress">
            <div className="progress-meta"><span>Progreso registrado</span><strong>{measuredProgress == null ? '—' : `${measuredProgress}%`}</strong></div>
            <div className="progress-track"><span style={{ width: `${measuredProgress || 0}%` }} /></div>
          </div>
          <div className="continue-meta"><span><Icon icon={IconRocket} size={14} />+{currentActivity.xp_reward || 0} XP</span><span>{getDifficultyLabel(currentActivity.difficulty)}</span></div>
          <button className="button button-light" onClick={() => onOpenActivity(currentActivity)} disabled={!filteredActivities.length}>Abrir reto <Icon icon={IconArrowRight} size={17} /></button>
          <div className="continue-decoration decoration-bracket" aria-hidden="true">&lt;/&gt;</div>
        </div>
        <GamificationCard gamification={gamification} />
        <div className="score-card">
          <div className="card-heading-row"><span className="card-overline">Tu colección</span><Icon icon={IconSchool} size={19} /></div>
          <div className="score-value">{gamification.completed_challenges}<span>retos</span></div>
          <div className="badge-strip" aria-label={`${gamification.badges.length} insignias conseguidas`}>
            {gamification.badges.slice(0, 4).map((badge) => <span className="badge-chip" key={badge.id} title={badge.description || badge.title}><Icon icon={IconCircleCheck} size={14} />{badge.title}</span>)}
            {!gamification.badges.length && <span className="badge-empty">Completa tu primer reto para desbloquear insignias.</span>}
          </div>
          <p>{gamification.badges.length ? `${gamification.badges.length} insignias desbloqueadas` : 'Las insignias aparecerán al superar retos.'}</p>
        </div>
      </section>
      <section className="section-block activities-section">
        <div className="section-heading"><div><p className="kicker">{TRACKS[activeTrack].shortLabel}</p><h2>Retos disponibles</h2></div>{filteredActivities.length > 0 && <span className="section-count">{filteredActivities.length} {filteredActivities.length === 1 ? 'reto' : 'retos'}</span>}</div>
        <div className="activity-list">
          {filteredActivities.length ? filteredActivities.map((activity) => <StudentActivityRow key={activity.id} activity={activity} onOpen={() => onOpenActivity(activity)} />) : <div className="empty-dashboard"><Icon icon={activeTrack === 'bash' ? IconTerminal2 : IconCode} size={19} /><span>{activeTrack === 'all' ? 'Cuando te asignen un reto, aparecerá aquí.' : `Todavía no hay retos de ${TRACKS[activeTrack].label}.`}</span></div>}
        </div>
      </section>
      <section className="student-lower-grid">
        <div className="tip-card"><span className="tip-mark"><Icon icon={activeTrack === 'bash' ? IconTerminal2 : IconInfoCircle} size={18} /></span><div><p className="card-overline">Pista del día</p><p>{(activeTrack === 'bash' ? ['No ejecutes scripts que no entiendas: revisa rutas, permisos y códigos de salida.', 'Una ruta entre comillas protege los espacios y evita sorpresas al hacer copias.'] : ['Si un elemento no se centra, revisa primero quién es su contenedor.', 'Prueba primero la estructura y después ajusta el estilo: un cambio cada vez.'])[tipIndex % 2]}</p></div><button className="icon-button" type="button" aria-label="Siguiente pista" onClick={() => setTipIndex((value) => value + 1)}><Icon icon={IconArrowRight} size={17} /></button></div>
        {filteredActivities[1] && <div className="next-card"><div><p className="card-overline">Siguiente reto</p><h3>{filteredActivities[1].title}</h3><p>{filteredActivities[1].module || 'Reto'}</p></div><span className="next-number">02</span></div>}
      </section>
    </div>
  )
}

function GamificationCard({ gamification }) {
  return <div className="gamification-card">
    <div className="card-heading-row"><span className="card-overline">Tu progreso</span><Icon icon={IconRocket} size={19} /></div>
    <div className="gamification-level"><span className="level-orb">{gamification.level}</span><div><span className="level-label">Nivel actual</span><strong>Nivel {gamification.level}</strong></div><span className="gamification-xp">{formatXp(gamification.total_xp)} XP</span></div>
    <div className="gamification-progress-meta"><span>Hasta el siguiente nivel</span><strong>{gamification.level_progress}%</strong></div>
    <div className="progress-track progress-track-light"><span style={{ width: `${gamification.level_progress}%` }} /></div>
    <p className="gamification-next">{gamification.xp_to_next_level ? `Te faltan ${formatXp(gamification.xp_to_next_level)} XP para subir.` : 'Sigue practicando para desbloquear el siguiente nivel.'}</p>
  </div>
}

function StudentActivityRow({ activity, onOpen }) {
  const status = getStudentStatus(activity.status)
  const language = trackForActivity(activity)
  const completed = activity.completed
  return (
    <button className="activity-row" onClick={onOpen} type="button">
      <span className={`activity-icon activity-icon-${language}`}><Icon icon={language === 'bash' ? IconTerminal2 : activity.id === 'semantic-html' ? IconBrandHtml5 : activity.id === 'dom-events' ? IconBrandJavascript : IconBrandCss3} size={22} /></span>
      <span className="activity-row-main"><span className="activity-row-title">{activity.title}</span><span className="activity-row-meta">{activity.module} <span className="meta-dot">·</span> {activity.summary}</span></span>
      <span className={`status-label status-${status.tone}`}><span className="status-dot" />{status.label}</span>
      <span className="activity-row-score">{activity.xp_reward ? <><strong>{formatXp(activity.earned_xp)} / {formatXp(activity.xp_reward)} XP</strong><small>{completed ? 'Reto completado' : 'XP logrados'}</small></> : activity.score != null ? `${Number(activity.score).toLocaleString('es-ES')}/10` : activity.progress != null ? `${activity.progress}%` : '—'}</span>
      <Icon icon={IconChevronRight} size={18} className="row-chevron" />
    </button>
  )
}

function getStudentStatus(status) {
  if (status === 'graded') return { label: 'Corregida', tone: 'mint' }
  if (status === 'submitted') return { label: 'Entregada', tone: 'mint' }
  if (status === 'in_progress') return { label: 'En curso', tone: 'gold' }
  if (status === 'overdue') return { label: 'Fuera de plazo', tone: 'red' }
  return { label: 'Sin empezar', tone: 'muted' }
}

function TeacherDashboard({ user, data, onOpenActivity }) {
  const assignments = data?.assignments || []
  const reviews = data?.reviews || []
  const pendingReviews = Number(data?.pending_reviews ?? reviews.length)
  const tableRows = DEMO_MODE ? DEMO_TEACHER_ROWS : []
  const totalSubmissions = assignments.reduce((sum, item) => sum + Number(item.submissions || 0), 0)
  const totalGraded = assignments.reduce((sum, item) => sum + Number(item.graded || 0), 0)
  return (
    <div className="dashboard-page teacher-page">
      <DashboardHeader eyebrow={`Panel docente · ${user.group || 'Profesorado'}`} title="Tu aula, de un vistazo." subtitle="Resumen de actividad de tus grupos." action={assignments.length && !DEMO_MODE ? { label: 'Exportar notas', icon: IconChartBar } : assignments.length || DEMO_MODE ? { label: 'Abrir actividad', icon: IconRocket } : null} onAction={() => { if (!DEMO_MODE && assignments.length) window.location.assign('/teacher/exports/?format=wide'); else onOpenActivity(assignments[0] || DEMO_ACTIVITIES[0]) }} />
      <section className="teacher-stats" aria-label="Indicadores del grupo">
        <StatCard label="Entregas por revisar" value={DEMO_MODE ? '8' : String(Math.max(0, totalSubmissions - totalGraded))} detail={DEMO_MODE ? '+3 desde ayer' : `${totalSubmissions} entregas registradas`} tone="gold" icon={IconFileCode} />
        <StatCard label="Progreso medio" value={DEMO_MODE ? '78%' : assignments.length ? `${Math.round((totalGraded / Math.max(totalSubmissions, 1)) * 100)}%` : '—'} detail={DEMO_MODE ? '+4% esta unidad' : 'Según actividad publicada'} tone="mint" icon={IconChartBar} />
        <StatCard label="Actividades activas" value={DEMO_MODE ? '12' : String(assignments.length)} detail={DEMO_MODE ? '90% conectados esta semana' : 'En tus grupos'} tone="blue" icon={IconUsers} />
        <StatCard label="Próximo hito" value={DEMO_MODE ? 'Viernes' : '—'} detail={DEMO_MODE ? 'Eventos y DOM · U03' : 'Sin fecha próxima'} tone="violet" icon={IconCalendarEvent} />
      </section>
      <section className="teacher-main-grid">
        <div className="panel panel-table">
          <div className="panel-heading"><div><p className="kicker">Seguimiento de {user.group || 'grupos asignados'}</p><h2>Actividad reciente</h2></div><span className="panel-heading-mark" title="Datos del servidor local"><Icon icon={IconChartBar} size={18} /></span></div>
          <div className="table-toolbar"><span className="filter-button filter-static">Todas las actividades <Icon icon={IconChevronDown} size={15} /></span><span className="filter-button filter-static">Todos los alumnos <Icon icon={IconChevronDown} size={15} /></span><span className="toolbar-spacer" /><span className="table-updated"><span className="pulse-dot pulse-dot-dark" />Actualizado ahora</span></div>
          <div className="data-table-wrap">
            <table className="data-table"><caption className="sr-only">Actividad reciente de los alumnos</caption><thead><tr><th scope="col">Alumno / actividad</th><th scope="col">Entregas</th><th scope="col">Corregidas</th><th scope="col">Estado</th></tr></thead><tbody>{tableRows.length ? tableRows.map((row) => <tr key={row.name}><td><span className="student-cell"><span className={`avatar avatar-${row.tone}`}>{row.initials}</span><strong>{row.name}</strong></span></td><td><GradePill value={row.box === 'En curso' ? 'En curso' : row.box === 'No iniciado' ? 'No iniciado' : row.box === 'Pendiente' ? 'Pendiente' : 1} integer /></td><td><GradePill value={row.semantic} /></td><td><GradePill value={row.box === 'En curso' ? 'En curso' : row.dom === 'Pendiente' ? 'Pendiente' : '—'} /></td></tr>) : assignments.length ? assignments.map((assignment) => <tr key={assignment.id}><td><span className="student-cell"><span className="avatar avatar-blue"><Icon icon={IconCode} size={14} /></span><strong>{assignment.title}</strong></span></td><td><GradePill value={assignment.submissions || 0} integer /></td><td><GradePill value={assignment.graded || 0} integer /></td><td><GradePill value={assignment.graded >= assignment.submissions && assignment.submissions ? 'Corregida' : assignment.submissions ? 'En curso' : 'No iniciado'} /></td></tr>) : <tr><td colSpan="4"><div className="empty-dashboard">No hay actividad publicada en tus grupos.</div></td></tr>}</tbody></table>
          </div>
          <a className="panel-footer-link" href="/teacher/exports/?format=wide">Ver matriz completa <Icon icon={IconArrowRight} size={15} /></a>
        </div>
        <aside className="teacher-side-column">
          <div className="panel due-panel"><div className="panel-heading"><div><p className="kicker">Atención</p><h2>Para revisar</h2></div><span className="count-badge">{DEMO_MODE ? 8 : pendingReviews}</span></div>{DEMO_MODE ? <div className="review-list"><ReviewItem initials="LG" name="Lucía García" activity="Modelo de caja con CSS" time="hace 12 min" tone="mint" onClick={() => onOpenActivity(DEMO_ACTIVITIES[0])} /><ReviewItem initials="AN" name="Álvaro Nieto" activity="Modelo de caja con CSS" time="hace 31 min" tone="amber" onClick={() => onOpenActivity(DEMO_ACTIVITIES[0])} /><ReviewItem initials="IC" name="Irene Castro" activity="Estructura semántica" time="ayer" tone="peach" onClick={() => onOpenActivity(DEMO_ACTIVITIES[1])} /></div> : reviews.length ? <div className="review-list">{reviews.slice(0, 3).map((review, index) => <ReviewItem key={review.id} initials={getInitials(review.student)} name={review.student} activity={`${review.assignment} · intento ${review.attempt_number}`} time={formatDate(review.submitted_at)} tone={['mint', 'amber', 'blue'][index % 3]} onClick={() => window.location.assign(review.url)} />)}</div> : <div className="empty-reviews">No hay entregas pendientes de publicación.</div>}{reviews[0] && <button className="panel-footer-link" type="button" onClick={() => window.location.assign(reviews[0].url)}>Abrir revisión <Icon icon={IconArrowRight} size={15} /></button>}</div>
          <div className="panel rhythm-panel"><div className="panel-heading"><div><p className="kicker">Ritmo del grupo</p><h2>Esta semana</h2></div><Icon icon={IconChartBar} size={19} /></div>{DEMO_MODE ? <><div className="rhythm-chart" aria-label="Gráfico de actividad de lunes a domingo">{[42, 55, 48, 78, 66, 31, 17].map((height, index) => <div className={`chart-column ${index === 3 ? 'is-current' : ''}`} key={index}><span style={{ height: `${height}%` }} /><small>{['L', 'M', 'X', 'J', 'V', 'S', 'D'][index]}</small></div>)}</div><p className="rhythm-caption"><strong>+18%</strong> de actividad frente a la semana pasada.</p></> : <p className="empty-reviews">El ritmo se mostrará cuando haya actividad registrada.</p>}</div>
        </aside>
      </section>
      <section className="teacher-bottom-grid">{reviews.length && !DEMO_MODE ? <div className="announce-card"><span className="announce-icon"><Icon icon={IconSchool} size={20} /></span><div><p className="card-overline">Siguiente revisión</p><h3>{reviews[0].student} · {reviews[0].assignment}</h3><p>Comprueba la evidencia y publica la calificación cuando esté lista.</p></div><button className="button button-dark button-small" onClick={() => window.location.assign(reviews[0].url)}>Revisar <Icon icon={IconArrowRight} size={15} /></button></div> : (assignments.length || DEMO_MODE) ? <div className="announce-card"><span className="announce-icon"><Icon icon={IconSchool} size={20} /></span><div><p className="card-overline">Estado del aula</p><h3>{DEMO_MODE ? 'Publicar «Eventos y DOM»' : 'Sin revisiones pendientes'}</h3><p>{DEMO_MODE ? 'La actividad está lista para el grupo. Revisa los tests antes de abrirla.' : 'Las entregas publicadas están disponibles en el CSV de calificaciones.'}</p></div></div> : <div className="announce-card announce-empty"><Icon icon={IconInfoCircle} size={20} /><p>No hay actividades disponibles para mostrar.</p></div>}<div className="teacher-note"><Icon icon={IconInfoCircle} size={18} /><p><strong>Consejo de aula</strong> · Los tests públicos funcionan mejor cuando explican el porqué.</p></div></section>
    </div>
  )
}

function StatCard({ label, value, detail, tone, icon }) {
  return <div className={`stat-card stat-${tone}`}><div className="stat-card-top"><span className="stat-label">{label}</span><span className="stat-icon"><Icon icon={icon} size={18} /></span></div><strong className="stat-value">{value}</strong><span className="stat-detail">{detail}</span></div>
}

function GradePill({ value, integer = false }) {
  if (value === 'Pendiente') return <span className="grade-pill grade-pending">Pendiente</span>
  if (value === 'No iniciado') return <span className="grade-pill grade-muted">No iniciado</span>
  if (value === 'En curso') return <span className="grade-pill grade-progress"><span className="activity-signal" />En curso</span>
  if (value === 'Corregida') return <span className="grade-pill grade-excellent">Corregida</span>
  if (value === '—') return <span className="grade-empty">—</span>
  const number = Number(value)
  if (integer) return <span className="grade-pill grade-good">{number.toLocaleString('es-ES', { maximumFractionDigits: 0 })}</span>
  return <span className={`grade-pill ${number >= 9 ? 'grade-excellent' : number >= 7 ? 'grade-good' : 'grade-risk'}`}>{number.toLocaleString('es-ES', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}</span>
}

function ReviewItem({ initials, name, activity, time, tone, onClick }) {
  return <button className="review-item" type="button" onClick={onClick}><span className={`avatar avatar-${tone}`}>{initials}</span><span className="review-copy"><strong>{name}</strong><small>{activity}</small><small className="review-time">{time}</small></span><Icon icon={IconChevronRight} size={16} /></button>
}

function SecondaryView({ view, isTeacher, data, onOpenActivity }) {
  const labels = { activities: ['Actividades', 'Todo el trabajo del aula, en un solo sitio.'], grades: [isTeacher ? 'Libro de calificaciones' : 'Mis notas', isTeacher ? 'Consulta, ajusta y exporta las evidencias del grupo.' : 'Tu progreso y las notas que ya has conseguido.'], group: ['Mi grupo', 'Las personas y el ritmo de tu aula.'], library: ['Biblioteca', 'Lecciones y recursos disponibles sin salir de la red del centro.'], history: ['Historial', 'Un registro sencillo de tus entregas y cambios.'], settings: ['Preferencias', 'Ajustes locales de tu experiencia de aprendizaje.'] }
  const [title, subtitle] = labels[view] || labels.activities
  return <div className="secondary-page"><div className="secondary-topline"><button className="back-link" type="button" onClick={() => window.history.back()}><Icon icon={IconArrowLeft} size={16} />Resumen</button></div><DashboardHeader eyebrow={isTeacher ? 'Espacio docente' : 'Mi espacio'} title={title} subtitle={subtitle} action={null} onAction={() => onOpenActivity(null)} />{view === 'activities' && !isTeacher ? <ActivityCatalog data={data} onOpenActivity={onOpenActivity} /> : <div className="secondary-placeholder"><span className="placeholder-mark"><Icon icon={view === 'grades' ? IconChartBar : view === 'group' ? IconUsers : IconCode} size={25} /></span><h2>Esta vista está lista para crecer contigo.</h2><p>La Fase 0 concentra el flujo completo de práctica: elegir un reto, escribir código, probarlo y entregar una evidencia.</p></div>}</div>
}

function ActivityCatalog({ data, onOpenActivity }) {
  const source = Array.isArray(data?.assignments) ? data.assignments : (DEMO_MODE ? DEMO_ACTIVITIES : [])
  const activities = source.map(assignmentWithDefaults)
  const [activeTrack, setActiveTrack] = useState('all')
  const visible = activeTrack === 'all' ? activities : activities.filter((activity) => trackForActivity(activity) === activeTrack)
  return <section className="catalog-section" aria-label="Catálogo de retos"><div className="catalog-toolbar"><div><span className="card-overline">Filtrar por recorrido</span><p>{visible.length} {visible.length === 1 ? 'reto disponible' : 'retos disponibles'}</p></div><div className="catalog-filters" role="group" aria-label="Filtrar retos"><button className={activeTrack === 'all' ? 'is-active' : ''} type="button" aria-pressed={activeTrack === 'all'} onClick={() => setActiveTrack('all')}>Todos</button><button className={activeTrack === 'web' ? 'is-active' : ''} type="button" aria-pressed={activeTrack === 'web'} onClick={() => setActiveTrack('web')}>Web · SMR</button><button className={activeTrack === 'bash' ? 'is-active' : ''} type="button" aria-pressed={activeTrack === 'bash'} onClick={() => setActiveTrack('bash')}>Bash · ASIR</button></div></div><div className="catalog-list">{visible.length ? visible.map((activity) => <StudentActivityRow key={activity.id} activity={activity} onOpen={() => onOpenActivity(activity)} />) : <div className="empty-dashboard"><Icon icon={activeTrack === 'bash' ? IconTerminal2 : IconCode} size={19} /><span>Todavía no hay retos en este itinerario.</span></div>}</div></section>
}

function WorkspaceShell({ user, activity, onBack, onLogout }) {
  const moduleLabel = activity.module || activity.activity?.module || 'Actividad'
  return <div className="workspace-shell"><header className="workspace-header"><div className="workspace-header-left"><button className="icon-button" onClick={onBack} aria-label="Volver al resumen"><Icon icon={IconArrowLeft} /></button><span className="workspace-breadcrumb"><span>Reto4V</span><Icon icon={IconChevronRight} size={14} /><span>{moduleLabel}</span><Icon icon={IconChevronRight} size={14} /><strong>{activity.title}</strong></span></div><div className="workspace-header-right"><span className="workspace-lan"><span className="pulse-dot pulse-dot-dark" />Solo LAN</span><button className="avatar avatar-small" onClick={onLogout} aria-label="Cerrar sesión">{getInitials(user.display_name)}</button></div></header><Workspace user={user} activity={activity} onBack={onBack} /></div>
}

function InstructionText({ value, className = 'instruction-rich-text', compact = false }) {
  const blocks = parseInstructionBlocks(value)
  return <div className={`${className}${compact ? ' instruction-rich-text-compact' : ''}`}>{blocks.length ? blocks.map((block, index) => {
    if (block.type === 'heading') return <h3 key={`${block.type}-${index}`}>{renderInlineText(block.text)}</h3>
    if (block.type === 'quote') return <blockquote key={`${block.type}-${index}`}>{renderInlineText(block.text)}</blockquote>
    if (block.type === 'list') return <ul key={`${block.type}-${index}`}>{block.items.map((item, itemIndex) => <li key={`${index}-${itemIndex}`}>{renderInlineText(item)}</li>)}</ul>
    return <p key={`${block.type}-${index}`}>{renderInlineText(block.text)}</p>
  }) : <p className="instruction-empty">No hay instrucciones publicadas para este reto.</p>}</div>
}

function parseInstructionBlocks(value) {
  const lines = String(value || '').split(/\r?\n/)
  const blocks = []
  let paragraph = []
  let quote = []
  let list = null
  const flushParagraph = () => { if (paragraph.length) blocks.push({ type: 'paragraph', text: paragraph.join(' ') }); paragraph = [] }
  const flushQuote = () => { if (quote.length) blocks.push({ type: 'quote', text: quote.join(' ') }); quote = [] }
  const flushList = () => { if (list?.length) blocks.push({ type: 'list', items: list }); list = null }
  const flushText = () => { flushParagraph(); flushQuote(); flushList() }
  for (const rawLine of lines) {
    const line = rawLine.trim()
    if (!line) { flushText(); continue }
    const heading = line.match(/^(#{1,4})\s+(.+)$/)
    if (heading) { flushText(); blocks.push({ type: 'heading', level: Math.min(3, heading[1].length), text: heading[2].trim() }); continue }
    const quoteLine = line.match(/^>\s*(.*)$/)
    if (quoteLine) { flushParagraph(); flushList(); quote.push(quoteLine[1]); continue }
    const listItem = line.match(/^(?:[-*]|\d+[.)])\s+(.+)$/)
    if (listItem) { flushParagraph(); flushQuote(); if (!list) list = []; list.push(listItem[1].trim()); continue }
    flushQuote(); flushList(); paragraph.push(line)
  }
  flushText()
  return blocks
}

function renderInlineText(value) {
  return String(value || '').split(/(`[^`]+`)/g).map((part, index) => part.startsWith('`') && part.endsWith('`') ? <code key={index}>{part.slice(1, -1)}</code> : <React.Fragment key={index}>{part}</React.Fragment>)
}

function Workspace({ activity, user }) {
  const initialLanguage = normalizeLanguage(activity.language || activity.track || activity.version?.language)
  const initialFiles = DEMO_MODE ? (initialLanguage === 'bash' ? BASH_FILES_DEFAULT : FILES_DEFAULT) : (initialLanguage === 'bash' ? { bash: '' } : { html: '', css: '', javascript: '' })
  const [language, setLanguage] = useState(initialLanguage)
  const [files, setFiles] = useState(initialFiles)
  const [starterFiles, setStarterFiles] = useState(initialFiles)
  const [activeFile, setActiveFile] = useState(initialLanguage === 'bash' ? 'bash' : 'html')
  const [revision, setRevision] = useState(activity.revision || 0)
  const revisionRef = useRef(revision)
  const [saveState, setSaveState] = useState('saved')
  const [saveMessage, setSaveMessage] = useState('Guardado')
  const [hydrated, setHydrated] = useState(false)
  const [serverDraft, setServerDraft] = useState(null)
  const [workspaceData, setWorkspaceData] = useState(null)
  const [conflict, setConflict] = useState(false)
  const [previewHtml, setPreviewHtml] = useState(() => initialLanguage === 'bash' ? '' : buildPreview(initialFiles))
  const [consoleEntries, setConsoleEntries] = useState([])
  const [tests, setTests] = useState([])
  const [testsState, setTestsState] = useState('idle')
  const [submitOpen, setSubmitOpen] = useState(false)
  const [submitState, setSubmitState] = useState('idle')
  const [notice, setNotice] = useState('')
  const [mobilePanel, setMobilePanel] = useState('instructions')
  const [showHistory, setShowHistory] = useState(false)
  const iframeRef = useRef(null)
  const isBash = language === 'bash'

  useEffect(() => { revisionRef.current = revision }, [revision])

  useEffect(() => {
    let active = true
    let loaded = false
    apiFetch(`${API_PREFIX}/assignments/${activity.id}/`).then((data) => {
      if (!active || !data) return
      loaded = true
      setWorkspaceData(data)
      const nextLanguage = normalizeLanguage(data.version?.language || data.language || activity.language)
      const nextStarterFiles = normalizeFiles(data.version?.files || data.activity?.files || {}, nextLanguage)
      const nextFiles = data.draft?.files ? normalizeFiles(data.draft.files, nextLanguage) : nextStarterFiles
      setLanguage(nextLanguage)
      setActiveFile(nextLanguage === 'bash' ? 'bash' : 'html')
      setStarterFiles(nextStarterFiles)
      setFiles(nextFiles)
      setRevision(Number(data.draft?.revision ?? data.revision ?? 0))
      revisionRef.current = Number(data.draft?.revision ?? data.revision ?? 0)
      if (nextLanguage === 'web') setPreviewHtml(buildPreview(nextFiles))
    }).catch(() => {
      // La vista de demostración usa el borrador inicial solo durante `vite dev`.
      if (!DEMO_MODE) {
        setSaveState('error')
        setSaveMessage('No se pudo cargar')
      }
    }).finally(() => { if (active) setHydrated(loaded || DEMO_MODE) })
    return () => { active = false }
  }, [activity.id])

  useEffect(() => {
    if (!hydrated) return undefined
    const timeout = window.setTimeout(() => persistDraft(files), 1100)
    return () => window.clearTimeout(timeout)
  }, [files, hydrated])

  useEffect(() => {
    const receiveConsoleEvent = (event) => {
      // El iframe sandbox tiene origen opaco: verificamos la ventana emisora y validamos el mensaje.
      if (event.source !== iframeRef.current?.contentWindow) return
      const message = event.data
      if (!message || message.channel !== 'aulaweb-preview' || typeof message.type !== 'string') return
      if (message.type !== 'console' && message.type !== 'runtime-error') return
      const level = ['log', 'info', 'warn', 'error'].includes(message.level) ? message.level : 'log'
      const value = typeof message.value === 'string' ? message.value.slice(0, 500) : JSON.stringify(message.value)?.slice(0, 500) || ''
      setConsoleEntries((current) => [...current, { id: `${Date.now()}-${Math.random()}`, level, value, type: message.type }].slice(-60))
    }
    window.addEventListener('message', receiveConsoleEvent)
    return () => window.removeEventListener('message', receiveConsoleEvent)
  }, [])

  const persistDraft = useCallback(async (nextFiles) => {
    if (!hydrated) return
    setSaveState('saving')
    setSaveMessage('Guardando…')
    try {
      const data = await apiFetch(`${API_PREFIX}/assignments/${activity.id}/draft/`, {
        method: 'POST',
        headers: { 'If-Match': `"${revisionRef.current}"` },
        body: JSON.stringify({ ...filesPayload(nextFiles, isBash), revision: revisionRef.current }),
      })
      const nextRevision = Number(data?.revision ?? revisionRef.current + 1)
      setRevision(nextRevision)
      revisionRef.current = nextRevision
      setSaveState('saved')
      setSaveMessage('Guardado')
      setConflict(false)
    } catch (error) {
      if (error.status === 409) {
        setServerDraft(normalizeFiles(error.payload?.current?.files || error.payload?.draft || error.payload || {}, isBash ? 'bash' : 'web'))
        const currentRevision = Number(error.payload?.revision)
        if (Number.isFinite(currentRevision)) {
          setRevision(currentRevision)
          revisionRef.current = currentRevision
        }
        setConflict(true)
        setSaveState('conflict')
        setSaveMessage('Hay una versión más reciente')
      } else {
        setSaveState('error')
        setSaveMessage('No se pudo guardar')
      }
    }
  }, [activity.id, hydrated, isBash])

  const changeFile = (key, value) => setFiles((current) => ({ ...current, [key]: value }))
  const runPreview = () => {
    if (isBash) return
    setConsoleEntries([])
    setPreviewHtml(buildPreview(files))
    setNotice('Preview actualizada')
  }

  const runTests = async () => {
    setTestsState('running')
    setNotice(isBash ? 'Analizando el script con las validaciones públicas…' : 'Ejecutando tests públicos…')
    try {
      const data = await apiFetch(`${API_PREFIX}/assignments/${activity.id}/tests/`, { method: 'POST', body: JSON.stringify(filesPayload(files, isBash)) })
      setTests(data?.results || [])
      setTestsState('done')
      setNotice(`${isBash ? 'Validaciones' : 'Tests'} finalizados · ${formatScore(data?.score)}/10`)
    } catch (error) {
      if (DEMO_MODE) {
        setTests(isBash ? DEMO_BASH_TESTS : DEMO_TESTS)
        setTestsState('done')
        setNotice(isBash ? 'Validaciones de demostración finalizadas · revisa el detalle' : 'Tests de demostración finalizados · 7/10')
      } else {
        setTestsState('error')
        setNotice(error.message || 'No se pudieron ejecutar las validaciones.')
      }
    }
  }

  const submit = async () => {
    setSubmitState('sending')
    try {
      const data = await apiFetch(`${API_PREFIX}/assignments/${activity.id}/submit/`, { method: 'POST', body: JSON.stringify(filesPayload(files, isBash)) })
      setSubmitState('success')
      setSubmitOpen(false)
      if (data?.submission) setWorkspaceData((current) => ({ ...current, submissions: [...(current?.submissions || []), data.submission], gamification: data.gamification || current?.gamification }))
      const attempt = data?.submission?.attempt_number
      setNotice(attempt ? `Entrega registrada correctamente · intento ${attempt}` : (data?.message || 'Entrega registrada correctamente'))
    } catch (error) {
      if (DEMO_MODE) {
        setSubmitState('success')
        setSubmitOpen(false)
        setNotice(`Entrega de demostración registrada · intento ${currentAttempt} de ${maxAttemptsLabel}`)
      } else {
        setSubmitState('error')
        setNotice(error.message || 'No se pudo registrar la entrega.')
      }
    }
  }

  const restoreServerDraft = () => {
    if (!serverDraft) return
    setFiles(serverDraft)
    setConflict(false)
    setSaveState('saved')
    setSaveMessage('Borrador recargado')
  }

  const useLocalCopy = async () => {
    setConflict(false)
    await persistDraft(files)
  }

  const activityVersion = workspaceData?.version || {}
  const effectiveLanguage = normalizeLanguage(activityVersion.language || language)
  const effectiveIsBash = effectiveLanguage === 'bash'
  const publicTests = activityVersion.public_tests || activityVersion.publicTests || []
  const visibleTests = tests.length ? tests : (publicTests.length ? publicTests : (DEMO_MODE ? (effectiveIsBash ? DEMO_BASH_TESTS : DEMO_TESTS) : []))
  const submissions = workspaceData?.submissions || []
  const maxAttempts = Number(workspaceData?.max_attempts ?? activity.max_attempts ?? activity.attempts ?? 0)
  const maxAttemptsLabel = maxAttempts > 0 ? maxAttempts : 'sin límite'
  const currentAttempt = Math.max(1, submissions.length + 1)
  const activeTestCount = visibleTests.length
  const passedTestCount = visibleTests.filter((test) => test.status === 'passed' || test.passed === true).length
  const instructions = activityVersion.instructions || activity.instructions || (effectiveIsBash ? 'Escribe un script Bash legible y seguro, y justifica las decisiones que tomes.' : 'Completa el reto siguiendo las indicaciones y prueba tu resultado antes de entregar.')
  const objectives = asList(activityVersion.objectives || activity.objectives)
  const hints = Array.isArray(activityVersion.hints || activity.hints) ? (activityVersion.hints || activity.hints) : []
  const challengeGamification = normalizeChallengeGamification(workspaceData || (DEMO_MODE ? { gamification: { xp_reward: activity.xp_reward, earned_xp: activity.earned_xp, completed: activity.completed, progress: activity.progress, language: effectiveLanguage, difficulty: activity.difficulty } } : null), activity)
  const xpReward = challengeGamification.xp_reward
  const earnedXp = challengeGamification.earned_xp
  const editorKeys = effectiveIsBash ? ['bash'] : Object.keys(FILE_META)
  const safeFiles = effectiveIsBash ? { bash: files.bash || '' } : files

  return (
    <main className="workspace-main">
      <div className="workspace-titlebar"><div><p className="kicker">{activity.module || activity.activity?.module || (effectiveIsBash ? 'Seguridad · ASIR' : 'Aplicaciones web · SMR')}</p><h1>{activity.title}</h1><p className="workspace-subtitle">{activity.summary || activity.description || (effectiveIsBash ? 'Resuelve el reto de scripting y deja una evidencia revisable.' : 'Completa el reto en el editor y comprueba el resultado antes de entregar.')}</p><div className="workspace-context-tags"><span className={`context-tag context-tag-${effectiveIsBash ? 'bash' : 'web'}`}><Icon icon={effectiveIsBash ? IconTerminal2 : IconCode} size={14} />{effectiveIsBash ? 'Bash · ASIR' : 'Web · SMR'}</span><span className="context-tag">{getDifficultyLabel(activity.difficulty || activityVersion.difficulty)}</span>{xpReward > 0 && <span className="context-tag context-tag-xp"><Icon icon={IconRocket} size={13} />{formatXp(earnedXp)} / {formatXp(xpReward)} XP</span>}<span className={`context-tag ${challengeGamification.completed ? 'context-tag-complete' : ''}`}>{challengeGamification.completed ? 'Reto completado' : `${challengeGamification.progress}% de progreso`}</span></div></div><div className="workspace-title-actions"><span className={`save-status save-${saveState}`}><span className="save-status-icon">{saveState === 'saving' ? <span className="mini-spinner" /> : saveState === 'error' || saveState === 'conflict' ? <Icon icon={IconAlertTriangle} size={15} /> : <Icon icon={IconDeviceFloppy} size={15} />}</span>{saveMessage}</span><button className="button button-outline" type="button" onClick={() => setShowHistory((current) => !current)}><Icon icon={IconHistory} size={16} />Historial</button></div></div>
      <div className="workspace-challenge-progress" aria-label={`Progreso del reto: ${challengeGamification.progress}%`}><div className="workspace-challenge-progress-copy"><span>Progreso del reto</span><strong>{challengeGamification.progress}%</strong></div><div className="progress-track"><span style={{ width: `${challengeGamification.progress}%` }} /></div>{challengeGamification.best_score != null && <small>Mejor nota: {formatScore(challengeGamification.best_score)}/10</small>}</div>
      {notice && <div className="workspace-notice" role="status"><Icon icon={IconInfoCircle} size={16} /><span>{notice}</span><button className="icon-button" aria-label="Cerrar aviso" onClick={() => setNotice('')}><Icon icon={IconX} size={15} /></button></div>}
      {!hydrated && <div className="workspace-loading" role="status"><span className="mini-spinner" />Cargando reto y borrador…</div>}
      {conflict && <div className="conflict-banner" role="alert"><span className="conflict-icon"><Icon icon={IconAlertTriangle} size={18} /></span><div><strong>Este borrador cambió en otra pestaña.</strong><p>Elige qué versión quieres conservar. No hemos sobrescrito tu trabajo.</p></div><div className="conflict-actions"><button className="button button-light button-small" onClick={restoreServerDraft}>Recargar servidor</button><button className="button button-dark button-small" onClick={useLocalCopy}>Conservar mi copia</button></div></div>}
      <div className={`workspace-mobile-tabs ${effectiveIsBash ? 'workspace-mobile-tabs-bash' : ''}`} role="tablist" aria-label="Panel del reto"><button className={mobilePanel === 'instructions' ? 'is-active' : ''} onClick={() => setMobilePanel('instructions')} role="tab">Reto</button><button className={mobilePanel === 'editor' ? 'is-active' : ''} onClick={() => setMobilePanel('editor')} role="tab">Editor</button><button className={mobilePanel === 'preview' ? 'is-active' : ''} onClick={() => setMobilePanel('preview')} role="tab">{effectiveIsBash ? 'Validación' : 'Preview'}</button></div>
      <section className="workspace-grid">
        <aside className={`instructions-panel workspace-panel ${mobilePanel === 'instructions' ? 'mobile-panel-visible' : ''}`}><div className="panel-label-row"><span className="panel-label">01 · Reto</span><span className="soft-pill pill-dark">{getDifficultyLabel(activity.difficulty || activityVersion.difficulty)}</span></div><h2>{activity.title || 'Tu reto de código'}</h2><InstructionText value={instructions} className="instruction-lede instruction-rich-text" />{objectives.length > 0 && <div className="instruction-section"><h3>Objetivos</h3><ul className="objective-list">{objectives.map((objective, index) => <li key={`${objective}-${index}`}><span>{String(index + 1).padStart(2, '0')}</span><InstructionText value={objective} compact /></li>)}</ul></div>}<div className="instruction-section"><h3>Qué tienes que conseguir</h3><ol className="challenge-list"><li><span>01</span><p>Lee el objetivo y tradúcelo a pequeñas decisiones de {effectiveIsBash ? 'scripting' : 'código'}.</p></li><li><span>02</span><p>{effectiveIsBash ? 'Revisa rutas, permisos y códigos de salida sin ejecutar el archivo desde la plataforma.' : 'Prueba cada cambio en la preview antes de pasar al siguiente.'}</p></li><li><span>03</span><p>Ejecuta las validaciones públicas y revisa el feedback.</p></li></ol></div><div className="instruction-section"><h3>Antes de entregar</h3><ul className="check-list"><li><Icon icon={IconCheck} size={15} />Tu resultado se entiende sin explicarlo.</li><li><Icon icon={IconCheck} size={15} />Has probado las validaciones públicas.</li><li><Icon icon={IconCheck} size={15} />El código está guardado.</li></ul></div>{hints.length > 0 ? <div className="hint-list">{hints.map((hint, index) => <details className="hint-block" key={`${hint}-${index}`}><summary><span className="hint-icon">?</span><strong>Pista {index + 1}</strong></summary><p>{typeof hint === 'string' ? hint : hint.text || hint.description || JSON.stringify(hint)}</p></details>)}</div> : <div className="hint-empty"><Icon icon={IconInfoCircle} size={15} /><span>Este reto no tiene pistas publicadas.</span></div>}<div className="instruction-footer"><span><Icon icon={IconClock} size={14} />{activity.duration || activity.estimated_minutes ? `${activity.duration || activity.estimated_minutes} min` : 'A tu ritmo'}</span><span><Icon icon={IconTestPipe} size={14} />{activeTestCount} validaciones</span></div></aside>
        <section className={`editor-panel workspace-panel ${mobilePanel === 'editor' ? 'mobile-panel-visible' : ''}`}><div className="editor-toolbar"><div className="file-tabs" role="tablist" aria-label="Archivos del reto">{editorKeys.map((key) => { const meta = effectiveIsBash ? BASH_FILE_META : FILE_META; const item = meta[key]; return <button key={key} className={`file-tab ${activeFile === key ? 'is-active' : ''} ${item.className}`} type="button" role="tab" aria-selected={activeFile === key} onClick={() => setActiveFile(key)}><Icon icon={item.icon} size={16} /><span>{item.label}</span></button> })}</div><button className="icon-button" type="button" title="Restaurar archivo inicial" aria-label="Restaurar archivo inicial" onClick={() => { setFiles(starterFiles); if (!effectiveIsBash) setPreviewHtml(buildPreview(starterFiles)); setNotice('Archivo inicial restaurado') }}><Icon icon={IconRefresh} size={17} /></button></div><div className="editor-stage"><CodeEditor file={activeFile} value={safeFiles[activeFile] || ''} language={effectiveLanguage} onChange={(value) => changeFile(activeFile, value)} /></div><div className="editor-footer"><span><Icon icon={IconInfoCircle} size={14} />Los cambios se guardan automáticamente</span><span className="editor-shortcuts">{effectiveIsBash ? <><Icon icon={IconTerminal2} size={13} />Nunca se ejecuta desde la plataforma</> : <><kbd>Ctrl</kbd><span>+</span><kbd>Enter</kbd> ejecutar</>}</span></div></section>
        {effectiveIsBash ? <BashValidationPanel source={safeFiles.bash || ''} mobileVisible={mobilePanel === 'preview'} /> : <aside className={`preview-panel workspace-panel ${mobilePanel === 'preview' ? 'mobile-panel-visible' : ''}`}><div className="preview-heading"><div><span className="panel-label">02 · Resultado</span><h2>Tu preview</h2></div><div className="preview-heading-actions"><span className="preview-isolation"><span className="pulse-dot pulse-dot-dark" />Aislada</span><button className="button button-outline button-small" type="button" onClick={runPreview}><Icon icon={IconPlayerPlay} size={14} />Ejecutar preview</button></div></div><div className="preview-frame-wrap"><iframe ref={iframeRef} title="Vista previa del código del alumno" sandbox="allow-scripts" srcDoc={previewHtml} /></div><div className="console-section"><div className="console-heading"><span><Icon icon={IconTerminal2} size={15} />Consola</span><button className="text-button text-button-muted" type="button" onClick={() => setConsoleEntries([])}>Limpiar</button></div><div className="console-output" aria-live="polite">{consoleEntries.length === 0 ? <span className="console-empty">Los mensajes de tu código aparecerán aquí.</span> : consoleEntries.map((entry) => <div className={`console-line console-${entry.level}`} key={entry.id}><span className="console-prefix">{entry.level === 'error' ? '×' : entry.level === 'warn' ? '!' : '›'}</span><span>{entry.value}</span></div>)}</div></div></aside>}
      </section>
      <section className="workspace-bottom"><div className="test-dock"><div className="test-dock-heading"><div><span className="panel-label">03 · Feedback</span><h2>{effectiveIsBash ? 'Validaciones públicas' : 'Tests públicos'}</h2></div><div className="test-summary">{testsState === 'running' ? <span className="running-test"><span className="mini-spinner" />Analizando…</span> : <><strong>{passedTestCount}/{activeTestCount}</strong> superadas</>}</div></div><div className="test-list">{visibleTests.length ? visibleTests.map((test, index) => <TestRow key={test.id || test.name || index} test={test} />) : <p className="empty-tests">{hydrated ? `Todavía no hay validaciones públicas para este reto.` : 'Cargando validaciones públicas…'}</p>}</div><div className="test-dock-actions"><button className="button button-outline" type="button" onClick={runTests} disabled={!hydrated || testsState === 'running'}><Icon icon={IconTestPipe} size={17} />{testsState === 'running' ? 'Analizando…' : effectiveIsBash ? 'Analizar script' : 'Ejecutar tests'}</button><button className="button button-dark" type="button" onClick={() => setSubmitOpen(true)} disabled={!hydrated}><Icon icon={IconRocket} size={17} />Entregar reto</button></div></div><div className="attempts-panel"><div className="attempts-heading"><div><span className="panel-label">04 · Evidencia</span><h2>Tus intentos</h2></div><span className="attempts-count">{submissions.length} / {maxAttemptsLabel}</span></div>{submissions.length ? submissions.map((submission) => <div className="attempt-row" key={submission.id || submission.attempt_number}><span className="attempt-number">{String(submission.attempt_number).padStart(2, '0')}</span><span className="attempt-copy"><strong>Entrega formal</strong><small>{formatDate(submission.submitted_at)}{submission.published_score != null ? ` · ${formatScore(submission.published_score)}/10` : ''}</small></span><span className="attempt-status attempt-good"><Icon icon={IconCircleCheck} size={15} />{submission.published_score != null ? formatScore(submission.published_score) : 'Enviada'}</span></div>) : <div className="empty-attempts"><Icon icon={IconHistory} size={18} /><span>Aún no hay entregas formales.</span></div>}<div className="attempt-row attempt-current"><span className="attempt-number">{String(currentAttempt).padStart(2, '0')}</span><span className="attempt-copy"><strong>Borrador actual</strong><small>Guardado en el servidor</small></span><span className="attempt-status"><span className="status-dot status-dot-gold" />En curso</span></div><button className="panel-footer-link" type="button" onClick={() => setShowHistory(true)}>Ver historial completo <Icon icon={IconArrowRight} size={15} /></button></div></section>
      {showHistory && <HistoryDrawer submissions={submissions} onClose={() => setShowHistory(false)} />}
      {submitOpen && <SubmitDialog activity={activity} attemptNumber={currentAttempt} maxAttempts={maxAttempts} isBash={effectiveIsBash} onCancel={() => setSubmitOpen(false)} onSubmit={submit} state={submitState} />}
    </main>
  )
}

const BASH_FILE_META = { bash: { label: 'script.sh', short: 'Bash', icon: IconTerminal2, className: 'file-bash' } }

function BashValidationPanel({ source, mobileVisible }) {
  const checks = inspectBash(source)
  return <aside className={`preview-panel workspace-panel bash-validation-panel ${mobileVisible ? 'mobile-panel-visible' : ''}`}><div className="preview-heading"><div><span className="panel-label">02 · Revisión</span><h2>Lectura estática</h2></div><span className="preview-isolation"><span className="pulse-dot pulse-dot-dark" />Sin ejecución</span></div><div className="bash-validation-body"><div className="bash-safety-note"><Icon icon={IconTerminal2} size={18} /><div><strong>El script no se ejecuta aquí</strong><p>Reto4V solo guarda y valida el texto. No hay terminal real ni salida simulada.</p></div></div><div className="bash-metrics"><span><strong>{checks.lines}</strong><small>líneas</small></span><span><strong>{checks.commands}</strong><small>comandos</small></span><span><strong>{checks.variables}</strong><small>variables</small></span></div><div className="bash-check-list" aria-label="Indicadores de lectura estática">{checks.items.map((check) => <div className={`bash-check bash-check-${check.state}`} key={check.id}><span className="bash-check-mark">{check.state === 'detected' ? <Icon icon={IconCircleCheck} size={16} /> : <Icon icon={IconClock} size={16} />}</span><span><strong>{check.label}</strong><small>{check.detail}</small></span></div>)}</div><p className="bash-validation-footnote"><Icon icon={IconInfoCircle} size={14} />La validación oficial y la nota se calculan en el servidor al analizar o entregar.</p></div></aside>
}

function inspectBash(source = '') {
  const text = String(source)
  const lines = text ? text.split(/\r?\n/).filter((line) => line.trim()).length : 0
  const commands = text ? (text.match(/(^|[;&|]\s*)(?:sudo\s+)?[a-zA-Z][a-zA-Z0-9_-]*/gm) || []).length : 0
  const variables = text ? (text.match(/\$\{?[A-Za-z_][A-Za-z0-9_]*\}?/g) || []).length : 0
  return {
    lines,
    commands,
    variables,
    items: [
      { id: 'shebang', label: 'Intérprete declarado', detail: text.startsWith('#!') ? 'Shebang detectado en la primera línea.' : 'Pendiente: empieza indicando el intérprete.', state: text.startsWith('#!') ? 'detected' : 'pending' },
      { id: 'safe-mode', label: 'Opciones de error', detail: /set\s+-[^\n]*(?:e|u)/.test(text) ? 'Se detectan opciones para controlar errores y variables.' : 'Revisa qué opciones necesita tu script.', state: /set\s+-[^\n]*(?:e|u)/.test(text) ? 'detected' : 'pending' },
      { id: 'quoted-paths', label: 'Variables revisables', detail: variables ? `${variables} referencias a variables para revisar.` : 'Todavía no se usan variables.', state: variables ? 'detected' : 'pending' },
      { id: 'archive-or-copy', label: 'Órdenes de archivo', detail: /\b(tar|rsync|cp|dd|zip|gzip)\b/.test(text) ? 'Se detecta una orden de copia o empaquetado.' : 'Indicador opcional: todavía no aparece una orden de archivo.', state: /\b(tar|rsync|cp|dd|zip|gzip)\b/.test(text) ? 'detected' : 'pending' },
      { id: 'exit-signal', label: 'Salida comprensible', detail: /\b(echo|printf|exit)\b/.test(text) ? 'Hay una señal de salida para quien revise el script.' : 'Añade una salida o código de retorno explicativo.', state: /\b(echo|printf|exit)\b/.test(text) ? 'detected' : 'pending' },
    ],
  }
}

function CodeEditor({ file, value, language = 'web', onChange }) {
  const editorRef = useRef(null)
  const viewRef = useRef(null)
  const valueRef = useRef(value)
  useEffect(() => { valueRef.current = value }, [value])
  useEffect(() => {
    if (!editorRef.current) return undefined
    const syntax = language === 'bash' ? bashLanguage() : file === 'html' ? html() : file === 'css' ? css() : javascript()
    const updateListener = EditorView.updateListener.of((update) => {
      if (update.docChanged) onChange(update.state.doc.toString())
    })
    const state = EditorState.create({ doc: valueRef.current, extensions: [
      lineNumbers(), highlightActiveLine(), drawSelection(), history(), indentOnInput(), bracketMatching(), autocompletion(), oneDark, syntax, syntaxHighlighting(defaultHighlightStyle, { fallback: true }), updateListener,
      keymap.of([...defaultKeymap, ...historyKeymap, indentWithTab]),
      EditorView.theme({ '&': { height: '100%', fontSize: '13px' }, '.cm-scroller': { overflow: 'auto', fontFamily: '"IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace' }, '.cm-gutters': { backgroundColor: '#152b40', color: '#5e7488', border: 'none' }, '.cm-activeLineGutter': { backgroundColor: '#1b344d', color: '#c4d3de' }, '.cm-activeLine': { backgroundColor: '#193148' } }),
    ] })
    const view = new EditorView({ state, parent: editorRef.current })
    viewRef.current = view
    return () => { view.destroy(); viewRef.current = null }
  }, [file, language])
  useEffect(() => {
    const view = viewRef.current
    if (!view) return
    const current = view.state.doc.toString()
    if (current !== value) view.dispatch({ changes: { from: 0, to: current.length, insert: value } })
  }, [value])
  return <div className="code-editor" ref={editorRef} aria-label={`Editor de ${language === 'bash' ? BASH_FILE_META.bash.label : FILE_META[file].label}`} />
}

const BASH_KEYWORDS = new Set(['if', 'then', 'elif', 'else', 'fi', 'for', 'while', 'until', 'in', 'do', 'done', 'case', 'esac', 'function', 'select', 'time'])
const BASH_BUILTINS = new Set(['echo', 'printf', 'read', 'export', 'local', 'declare', 'readonly', 'source', 'return', 'exit', 'cd', 'pwd', 'test', 'set', 'shift', 'trap', 'mkdir', 'rm', 'cp', 'mv', 'tar', 'rsync', 'find', 'grep', 'awk', 'sed', 'chmod', 'chown', 'date'])

const bashMode = {
  startState: () => ({}),
  token(stream) {
    if (stream.sol() && stream.match(/^#!.*$/)) return 'meta'
    if (stream.eatSpace()) return null
    if (stream.match(/^#.*/)) return 'comment'
    if (stream.match(/^"(?:\\.|[^"\\])*"|^'(?:[^'\\]|\\.)*'/)) return 'string'
    if (stream.match(/^\$\{?[A-Za-z_][A-Za-z0-9_]*\}?|^\$[0-9@*#?!-]/)) return 'variableName'
    if (stream.match(/^(?:&&|\|\||\||[|;&<>]|\(\(|\)\))/)) return 'operator'
    const word = stream.match(/^[A-Za-z_][A-Za-z0-9_-]*/)
    if (word) {
      if (BASH_KEYWORDS.has(word[0])) return 'keyword'
      if (BASH_BUILTINS.has(word[0])) return 'function'
      return null
    }
    stream.next()
    return null
  },
}

function bashLanguage() {
  return StreamLanguage.define(bashMode)
}

function TestRow({ test }) {
  const status = test.status || (typeof test.passed === 'boolean' ? (test.passed ? 'passed' : 'failed') : 'pending')
  return <div className={`test-row test-${status}`}><span className="test-icon">{status === 'passed' ? <Icon icon={IconCircleCheck} size={18} /> : status === 'failed' ? <Icon icon={IconCircleX} size={18} /> : <Icon icon={IconClock} size={17} />}</span><span className="test-copy"><strong>{test.title || test.name}</strong><small>{test.description || test.feedback || 'Sin detalles adicionales.'}</small></span><span className="test-points">{test.points ?? test.max_points ?? 0} pt</span></div>
}

function HistoryDrawer({ submissions = [], onClose }) {
  return <div className="drawer-backdrop" role="presentation" onClick={onClose}><aside className="history-drawer" role="dialog" aria-modal="true" aria-labelledby="history-title" onClick={(event) => event.stopPropagation()}><div className="drawer-heading"><div><span className="panel-label">Evidencias</span><h2 id="history-title">Historial de intentos</h2></div><button className="icon-button" type="button" onClick={onClose} aria-label="Cerrar historial"><Icon icon={IconX} /></button></div><p className="drawer-lede">Cada entrega conserva el código exacto, los tests y el momento en que se guardó.</p><div className="history-timeline">{submissions.length ? submissions.map((submission) => <HistoryItem key={submission.id || submission.attempt_number} number={String(submission.attempt_number).padStart(2, '0')} title="Entrega registrada" detail={formatDate(submission.submitted_at)} score={submission.published_score != null ? `${formatScore(submission.published_score)} / 10` : 'Enviada'} />) : <p className="empty-history">Aún no hay entregas formales para mostrar.</p>}<HistoryItem number={String(Math.max(1, submissions.length + 1)).padStart(2, '0')} title="Borrador actual" detail="Todavía editable" score="En curso" current /></div><div className="drawer-note"><Icon icon={IconInfoCircle} size={17} /><span>Las entregas no se pueden editar después de enviarlas.</span></div></aside></div>
}

function HistoryItem({ number, title, detail, score, current }) {
  return <div className={`history-item ${current ? 'is-current' : ''}`}><span className="history-line" /><span className="history-number">{number}</span><div className="history-copy"><strong>{title}</strong><small>{detail}</small></div><span className={current ? 'history-status' : 'history-score'}>{score}</span></div>
}

function SubmitDialog({ activity, attemptNumber, maxAttempts, isBash = false, onCancel, onSubmit, state }) {
  const maxAttemptsLabel = maxAttempts > 0 ? maxAttempts : 'sin límite'
  const isError = state === 'error'
  return <div className="dialog-backdrop"><div className="submit-dialog" role="dialog" aria-modal="true" aria-labelledby="submit-title"><button className="icon-button dialog-close" onClick={onCancel} aria-label="Cancelar entrega"><Icon icon={IconX} /></button><span className={`dialog-icon ${isError ? 'dialog-icon-error' : ''}`}>{isError ? <Icon icon={IconAlertTriangle} size={24} /> : <Icon icon={isBash ? IconTerminal2 : IconRocket} size={24} />}</span><p className="kicker">Entrega formal</p><h2 id="submit-title">{isError ? 'No se pudo entregar' : '¿Listo para entregar?'}</h2><p>{isError ? 'Revisa el mensaje del reto y vuelve a intentarlo cuando el servidor esté disponible.' : <>Se guardará {isBash ? 'el script actual' : 'el código actual'} como el <strong>intento {String(attemptNumber).padStart(2, '0')} de {maxAttemptsLabel}</strong>. Después podrás ver esta evidencia, pero no editarla.</>}</p><div className="submit-checks"><span><Icon icon={IconCheck} size={15} />{isBash ? '1 archivo incluido' : '3 archivos incluidos'}</span><span><Icon icon={IconTestPipe} size={15} />Validaciones públicas disponibles</span><span><Icon icon={IconClock} size={15} />Fecha del servidor</span></div><div className="dialog-actions"><button className="button button-outline" onClick={onCancel}>Volver al editor</button>{!isError && <button className="button button-dark" onClick={onSubmit} disabled={state === 'sending'}>{state === 'sending' ? <span className="button-loader" /> : <Icon icon={isBash ? IconTerminal2 : IconRocket} size={17} />}{state === 'sending' ? 'Enviando…' : `Entregar ${activity.title}`}</button>}</div></div></div>
}

function normalizeFiles(data, language = 'web') {
  const value = data && typeof data === 'object' ? data : {}
  if (normalizeLanguage(language) === 'bash') return { bash: typeof value.bash === 'string' ? value.bash : typeof value.script === 'string' ? value.script : '' }
  return { html: typeof value.html === 'string' ? value.html : '', css: typeof value.css === 'string' ? value.css : '', javascript: typeof value.javascript === 'string' ? value.javascript : typeof value.js === 'string' ? value.js : '' }
}

function filesPayload(files, isBash = false) {
  return isBash ? { bash: typeof files?.bash === 'string' ? files.bash : '' } : { html: files?.html || '', css: files?.css || '', javascript: files?.javascript || '' }
}

function asList(value) {
  if (Array.isArray(value)) return value.filter((item) => item != null).map((item) => typeof item === 'string' ? item : item.text || item.description || JSON.stringify(item))
  if (typeof value === 'string' && value.trim()) return [value]
  return []
}

function formatScore(score) {
  const value = Number(score)
  return Number.isFinite(value) ? value.toLocaleString('es-ES', { maximumFractionDigits: 2 }) : '0'
}

function formatXp(value) {
  const number = Number(value)
  return Number.isFinite(number) ? Math.round(number).toLocaleString('es-ES') : '0'
}

function buildPreview(files) {
  const htmlContent = typeof files?.html === 'string' ? files.html : ''
  const cssContent = typeof files?.css === 'string' ? files.css : ''
  const safeJavascript = (typeof files?.javascript === 'string' ? files.javascript : '').replace(/<\/script/gi, '<\\/script')
  const nonceAttribute = PREVIEW_NONCE ? ` nonce="${PREVIEW_NONCE}"` : ''
  const scriptPolicy = PREVIEW_NONCE ? `'nonce-${PREVIEW_NONCE}'` : "'unsafe-inline'"
  const bridge = `\n<script${nonceAttribute}>\n(() => {\n  const send = (type, level, value) => {\n    try { window.parent.postMessage({ channel: 'aulaweb-preview', type, level, value: String(value).slice(0, 500) }, '*') } catch (_) {}\n  };\n  ['log', 'info', 'warn', 'error'].forEach((level) => {\n    const original = console[level];\n    console[level] = (...values) => {\n      send('console', level, values.map((value) => typeof value === 'object' ? JSON.stringify(value) : value).join(' '));\n      original.apply(console, values);\n    };\n  });\n  window.addEventListener('error', (event) => send('runtime-error', 'error', event.message || 'Error de ejecución'));\n  window.addEventListener('unhandledrejection', (event) => send('runtime-error', 'error', event.reason || 'Promesa rechazada'));\n})();\n</script>`
  return `<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; base-uri 'none'; form-action 'none'; style-src 'unsafe-inline'; script-src ${scriptPolicy}; img-src data: blob:; connect-src 'none'; font-src 'none';"><style>${cssContent}</style></head><body>${htmlContent}${bridge}<script${nonceAttribute}>${safeJavascript}</script></body></html>`
}

function AppIconDots(props) {
  return <span className="dot-menu" aria-hidden="true"><i /><i /><i /></span>
}

const IconDotsIcon = AppIconDots

const IconBook2 = IconSchool

function formatDate(value) {
  if (!value) return 'Sin fecha'
  const date = new Date(value)
  if (Number.isNaN(date.valueOf())) return String(value)
  return new Intl.DateTimeFormat('es-ES', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

createRoot(document.getElementById('root')).render(<App />)
