export function parseInstructionBlocks(value) {
  const lines = String(value || '').split(/\r?\n/)
  const blocks = []
  let paragraph = []
  let quote = []
  let list = null
  let code = null

  const flushParagraph = () => {
    if (paragraph.length) blocks.push({ type: 'paragraph', text: paragraph.join(' ') })
    paragraph = []
  }
  const flushQuote = () => {
    if (quote.length) blocks.push({ type: 'quote', text: quote.join(' ') })
    quote = []
  }
  const flushList = () => {
    if (list?.length) blocks.push({ type: 'list', items: list })
    list = null
  }
  const flushText = () => {
    flushParagraph()
    flushQuote()
    flushList()
  }
  const flushCode = () => {
    if (code) blocks.push({ type: 'code', language: code.language, text: code.lines.join('\n') })
    code = null
  }

  for (const rawLine of lines) {
    if (code) {
      if (rawLine.trim() === '```') flushCode()
      else code.lines.push(rawLine)
      continue
    }

    const line = rawLine.trim()
    const fence = line.match(/^```([a-z0-9_-]*)$/i)
    if (fence) {
      flushText()
      code = { language: fence[1].toLowerCase(), lines: [] }
      continue
    }
    if (!line) {
      flushText()
      continue
    }
    const heading = line.match(/^(#{1,4})\s+(.+)$/)
    if (heading) {
      flushText()
      blocks.push({ type: 'heading', level: Math.min(3, heading[1].length), text: heading[2].trim() })
      continue
    }
    const quoteLine = line.match(/^>\s*(.*)$/)
    if (quoteLine) {
      flushParagraph()
      flushList()
      quote.push(quoteLine[1])
      continue
    }
    const listItem = line.match(/^(?:[-*]|\d+[.)])\s+(.+)$/)
    if (listItem) {
      flushParagraph()
      flushQuote()
      if (!list) list = []
      list.push(listItem[1].trim())
      continue
    }
    flushQuote()
    flushList()
    paragraph.push(line)
  }

  if (code) flushCode()
  flushText()
  return blocks
}
