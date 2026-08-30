import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const source = await readFile(new URL('../src/main.jsx', import.meta.url), 'utf8')

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

test('los dos itinerarios usan archivos y copy de producto propios', () => {
  assert.match(source, /language: 'bash'/)
  assert.match(source, /BASH_FILE_META/)
  assert.match(source, /filesPayload\(.*isBash/)
  assert.match(source, /script\.sh/)
  assert.match(source, /El script no se ejecuta aquí/)
  assert.match(source, /Reto4V/)
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
})
