import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('../src/main.jsx', import.meta.url), 'utf8')
const styles = await readFile(new URL('../src/styles.css', import.meta.url), 'utf8')

test('la preview usa sandbox con scripts pero sin same-origin', () => {
  assert.match(source, /sandbox="allow-scripts"/)
  assert.doesNotMatch(source, /sandbox="[^"]*allow-same-origin/)
  assert.match(source, /Content-Security-Policy/)
  assert.match(source, /connect-src 'none'/)
  assert.match(source, /nonceAttribute/)
})

test('los eventos de consola del iframe se validan antes de pintarse', () => {
  assert.match(source, /event\.source !== iframeRef\.current\?\.contentWindow/)
  assert.match(source, /message\.channel !== 'aulaweb-preview'/)
  assert.match(source, /slice\(0, 500\)/)
})

test('el guardado y la entrega usan el contrato JSON local', () => {
  assert.match(source, /assignments\/\$\{activity\.id\}\/draft/)
  assert.match(source, /assignments\/\$\{activity\.id\}\/tests/)
  assert.match(source, /assignments\/\$\{activity\.id\}\/submit/)
  assert.match(source, /revision: revisionRef\.current/)
})

test('los tres itinerarios usan archivos y copy de producto propios', () => {
  assert.match(source, /language: 'bash'/)
  assert.match(source, /BASH_FILE_META/)
  assert.match(source, /filesPayload\(files, language\)/)
  assert.match(source, /script\.sh/)
  assert.match(source, /El script no se ejecuta aquí/)
  assert.match(source, /language: 'python'/)
  assert.match(source, /PYTHON_FILE_META/)
  assert.match(source, /main\.py/)
  assert.match(source, /PythonAnalysisPanel/)
  assert.match(source, /El código Python no se ejecuta aquí/)
  assert.match(source, /filesPayload\(files, language\)/)
  assert.match(source, /Programmy4V/)
  assert.doesNotMatch(source, /Reto4V/)
})

test('la gamificación se pinta desde el contrato del servidor', () => {
  assert.match(source, /normalizeGamification/)
  assert.match(source, /total_xp/)
  assert.match(source, /level_progress/)
  assert.match(source, /xp_to_next_level/)
  assert.match(source, /completed_challenges/)
  assert.match(source, /activeTrack/)
  assert.match(source, /Todos los retos/)
  assert.match(source, /Bash · ASIR/)
  assert.match(source, /Python · DAM/)
  assert.match(source, /0491 · SGE/)
})

test('el alumno solo ve los itinerarios que tiene asignados', () => {
  assert.match(source, /availableTrackEntries = Object\.entries\(TRACKS\)\.filter/)
  assert.match(source, /activities\.some\(\(activity\) => trackForActivity\(activity\) === key\)/)
  assert.match(source, /El administrador debe asignarte un ciclo e itinerario/)
  assert.match(source, /Empezar primer reto/)
})

test('Web ofrece un comienzo guiado y un lenguaje cercano', () => {
  assert.match(source, /const WEB_WORKSPACE_COPY = \{/)
  assert.match(source, /No hace falta saberlo todo ni preparar carpetas en tu ordenador/)
  assert.match(source, /Sigue estos pasos/)
  assert.match(source, /Comprobar mi trabajo/)
  assert.match(source, /Así queda tu página/)
  assert.match(source, /const isWeb = effectiveLanguage === 'web'/)
  assert.match(source, /activityVersion\.editor_files/)
  assert.match(source, /editorFileCount=\{editorKeys\.length\}/)
  assert.match(source, /testCount=\{activeTestCount\}/)
  assert.match(source, /: \['html'\]/)
  assert.match(source, /const STATIC_WORKSPACE_COPY = \{/)
  assert.match(source, /Comprobar mi script/)
  assert.match(source, /Comprobar mi archivo/)
  assert.match(source, /submitChecks: 'Comprobaciones disponibles'/)
  assert.match(source, /!hasRealInstructions && <div className="instruction-section"><h3>\{workspaceCopy\.stepsTitle\}/)
  assert.match(source, /!isWeb \|\| !hasRealInstructions/)
  assert.match(source, /submitDate: 'Fecha de entrega'/)
  assert.match(source, /submitChecksEmpty: 'No hay comprobaciones para este ejercicio\.'/)
  assert.match(source, /submitError: 'No hemos podido guardar tu entrega/)
  assert.doesNotMatch(source, /Fecha del servidor/)
  assert.doesNotMatch(source, /Validaciones públicas disponibles/)
  assert.match(source, /Nunca se ejecuta desde la plataforma/)
})

test('Python mantiene el archivo aislado y solo ofrece análisis indicativo', () => {
  assert.match(source, /normalizeLanguage\(value\)/)
  assert.match(source, /normalized === 'bash' \|\| normalized === 'python'/)
  assert.match(source, /function inspectPython\(source = ''\)/)
  assert.match(source, /No hay intérprete, archivos reales ni salida simulada/)
  assert.match(source, /Nunca se ejecuta desde la plataforma/)
  assert.match(source, /effectiveIsPython \? <PythonAnalysisPanel/)
  assert.match(source, /checks\.operations/)
  assert.doesNotMatch(source, /checks\.files/)
})

test('los itinerarios conservan legibilidad móvil y acento visual Python', () => {
  assert.match(styles, /@media \(max-width: 740px\)[\s\S]*?\.track-options \{ grid-template-columns: repeat\(2, minmax\(0, 1fr\)\); \}/)
  assert.doesNotMatch(styles, /\.track-options \{ grid-template-columns: repeat\(3,/)
  assert.match(styles, /\.tip-mark-python \{ background: #e9e4f7; color: #6757a7; \}/)
})
