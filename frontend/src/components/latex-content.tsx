'use client'

import { useEffect, useRef } from 'react'
import renderMathInElement from 'katex/contrib/auto-render'

type LatexContentProps = {
  text?: string | null
  className?: string
}

const BOLD_OPEN_TOKEN = '@@__BOLD_OPEN__@@'
const BOLD_CLOSE_TOKEN = '@@__BOLD_CLOSE__@@'

function convertTextbfToTokens(input: string): string {
  const command = '\\textbf{'
  let cursor = 0
  let output = ''

  while (cursor < input.length) {
    const start = input.indexOf(command, cursor)
    if (start === -1) {
      output += input.slice(cursor)
      break
    }

    output += input.slice(cursor, start)
    let index = start + command.length
    let depth = 1

    while (index < input.length && depth > 0) {
      const ch = input[index]
      if (ch === '{') depth += 1
      if (ch === '}') depth -= 1
      index += 1
    }

    if (depth !== 0) {
      output += input.slice(start)
      break
    }

    const inner = input.slice(start + command.length, index - 1)
    output += `${BOLD_OPEN_TOKEN}${convertTextbfToTokens(inner)}${BOLD_CLOSE_TOKEN}`
    cursor = index
  }

  return output
}

function toSafeHtml(input: string): string {
  return input
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
    .replaceAll(BOLD_OPEN_TOKEN, '<strong>')
    .replaceAll(BOLD_CLOSE_TOKEN, '</strong>')
}

function normalizeTextCommands(input: string): string {
  const withFixedTypos = input
    .replace(/\\vsapce\b/gi, '\\vspace')
    .replace(/\\begin\{enumerate\}\s*\(\s*item\s*\)/gi, '\\begin{enumerate}\n\\item ')
    .replace(/\\begin\{itemize\}\s*\(\s*item\s*\)/gi, '\\begin{itemize}\n\\item ')

  const withSpacingAndBold = convertTextbfToTokens(
    withFixedTypos
      .replace(/\\vspace\*?\{[^}]*\}/gi, '\n')
      .replace(/\\bigskip\b/gi, '\n\n')
  )

  const lines = withSpacingAndBold.replace(/\r\n/g, '\n').split('\n')
  const normalized: string[] = []
  let listMode: 'enumerate' | 'itemize' | null = null
  let enumerateIndex = 0

  for (const line of lines) {
    const trimmed = line.trim()

    if (/\\begin\{enumerate\}/i.test(trimmed)) {
      listMode = 'enumerate'
      enumerateIndex = 0
      const trailing = line.replace(/.*\\begin\{enumerate\}/i, '').trim()
      if (!trailing) continue
      const itemMatch = trailing.match(/^(?:\\item|\(?item\)?)\s*(.*)$/i)
      if (itemMatch) {
        enumerateIndex += 1
        normalized.push(`${enumerateIndex}. ${itemMatch[1]}`.trimEnd())
      } else {
        normalized.push(trailing)
      }
      continue
    }

    if (/\\begin\{itemize\}/i.test(trimmed)) {
      listMode = 'itemize'
      const trailing = line.replace(/.*\\begin\{itemize\}/i, '').trim()
      if (!trailing) continue
      const itemMatch = trailing.match(/^(?:\\item|\(?item\)?)\s*(.*)$/i)
      if (itemMatch) {
        normalized.push(`- ${itemMatch[1]}`.trimEnd())
      } else {
        normalized.push(trailing)
      }
      continue
    }

    if (/\\end\{enumerate\}/i.test(trimmed) || /\\end\{itemize\}/i.test(trimmed)) {
      listMode = null
      continue
    }

    if (listMode) {
      const itemMatch = line.match(/^\s*(?:\\item|\(?item\)?)\s*(.*)$/i)
      if (itemMatch) {
        if (listMode === 'enumerate') {
          enumerateIndex += 1
          normalized.push(`${enumerateIndex}. ${itemMatch[1]}`.trimEnd())
        } else {
          normalized.push(`- ${itemMatch[1]}`.trimEnd())
        }
        continue
      }

      if (trimmed && normalized.length > 0) {
        normalized[normalized.length - 1] = `${normalized[normalized.length - 1]}\n${trimmed}`
        continue
      }
    }

    normalized.push(line)
  }

  return normalized.join('\n')
}

function normalizeLooseLatex(input: string): string {
  const withInlineSectionDividers = normalizeTextCommands(input)
    .replace(/\\answer\b/gi, '\n\\answer\n')
    .replace(/\\analysis\b/gi, '\n\\analysis\n')

  const withSectionDividers = withInlineSectionDividers
    .replace(/^\s*\\answer\s*:?\s*$/gim, '──────── 答案 ────────')
    .replace(/^\s*\\analysis\s*:?\s*$/gim, '──────── 解析 ────────')

  const hasStandardDelimiters =
    withSectionDividers.includes('$$') ||
    withSectionDividers.includes('$') ||
    withSectionDividers.includes('\\(') ||
    withSectionDividers.includes('\\)') ||
    withSectionDividers.includes('\\[') ||
    withSectionDividers.includes('\\]')

  const lines = withSectionDividers.replace(/\r\n/g, '\n').split('\n')
  const normalized: string[] = []
  let convertedToDisplayBlock = false

  for (let i = 0; i < lines.length; i += 1) {
    const current = lines[i].trim()

    // Support loose block style:
    // [formula...
    // ...formula]
    if (current.startsWith('[') && !current.endsWith(']')) {
      const block: string[] = []
      const first = lines[i].replace(/^\s*\[/, '')
      if (first.trim()) block.push(first)
      i += 1
      while (i < lines.length && !lines[i].trim().includes(']')) {
        block.push(lines[i])
        i += 1
      }
      if (i < lines.length) {
        const last = lines[i].replace(/\]\s*$/, '')
        if (last.trim()) block.push(last)
      }
      if (block.length > 0) {
        normalized.push('$$')
        normalized.push(block.join('\n').trim())
        normalized.push('$$')
        convertedToDisplayBlock = true
      }
      continue
    }

    if (current === '[') {
      const block: string[] = []
      i += 1
      while (i < lines.length && lines[i].trim() !== ']') {
        block.push(lines[i])
        i += 1
      }
      if (block.length > 0) {
        normalized.push('$$')
        normalized.push(block.join('\n').trim())
        normalized.push('$$')
        convertedToDisplayBlock = true
      }
      continue
    }

    const inlineBlock = current.match(/^\[(.+)\]$/)
    if (inlineBlock) {
      normalized.push(`$$${inlineBlock[1].trim()}$$`)
      convertedToDisplayBlock = true
      continue
    }

    normalized.push(lines[i])
  }

  const merged = normalized.join('\n')
  if (hasStandardDelimiters || convertedToDisplayBlock || merged.includes('$$')) return merged

  const replaceInlineParen = (source: string, pattern: RegExp) =>
    source.replace(pattern, (match, content) => {
      const value = content.trim()
      const isCompact = value.length <= 40
      const isFormulaLike = /[\\^_+\-*/={}]/.test(value) || value.length <= 2
      return isCompact && isFormulaLike ? `$${value}$` : match
    })

  return replaceInlineParen(
    replaceInlineParen(merged, /\(([A-Za-z0-9\\^_+\-*/={}.,:\s]+)\)/g),
    /（([A-Za-z0-9\\^_+\-*/={}.,:\s]+)）/g
  )
}

export function LatexContent({ text, className }: LatexContentProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const safeText = normalizeLooseLatex(text ?? '')
    el.innerHTML = toSafeHtml(safeText)
    renderMathInElement(el, {
      delimiters: [
        { left: '$$', right: '$$', display: true },
        { left: '\\[', right: '\\]', display: true },
        { left: '\\(', right: '\\)', display: false },
        { left: '$', right: '$', display: false },
      ],
      throwOnError: false,
    })
  }, [text])

  return (
    <div
      ref={containerRef}
      className={className}
      style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}
    />
  )
}
