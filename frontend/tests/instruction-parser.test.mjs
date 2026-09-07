import test from 'node:test'
import assert from 'node:assert/strict'
import { parseInstructionBlocks } from '../src/instruction-parser.js'

test('parsea fences de código como bloques independientes y conserva espacios', () => {
  const blocks = parseInstructionBlocks([
    '## Ejemplo',
    'Explicación antes.',
    '',
    '```html',
    '<main>',
    '  <h1>Hola</h1>',
    '</main>',
    '```',
    '',
    'Explicación después.',
  ].join('\n'))

  assert.deepEqual(blocks, [
    { type: 'heading', level: 2, text: 'Ejemplo' },
    { type: 'paragraph', text: 'Explicación antes.' },
    { type: 'code', language: 'html', text: '<main>\n  <h1>Hola</h1>\n</main>' },
    { type: 'paragraph', text: 'Explicación después.' },
  ])
})

test('admite fences Python y Bash y conserva líneas vacías internas', () => {
  const blocks = parseInstructionBlocks('```python\ndef saludo():\n    return "hola"\n\n\nprint(saludo())\n```\n\n```bash\nprintf \'%s\\n\' "hola"\n```')

  assert.equal(blocks[0].type, 'code')
  assert.equal(blocks[0].language, 'python')
  assert.equal(blocks[0].text, 'def saludo():\n    return "hola"\n\n\nprint(saludo())')
  assert.deepEqual(blocks[1], { type: 'code', language: 'bash', text: "printf '%s\\n' \"hola\"" })
})

test('un fence sin cierre sigue siendo código literal hasta el final', () => {
  assert.deepEqual(parseInstructionBlocks('Antes\n```html\n  <p>sin cierre</p>'), [
    { type: 'paragraph', text: 'Antes' },
    { type: 'code', language: 'html', text: '  <p>sin cierre</p>' },
  ])
})
