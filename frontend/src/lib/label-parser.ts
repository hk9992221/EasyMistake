function cleanLabel(value: string): string {
  return value
    .replace(/^[\s\-*•·✅☑✔]+/, '')
    .replace(/^\d+[\.\)、\s]+/, '')
    .replace(/^(总结|知识点|核心知识点|本题核心知识点)\s*[：:]\s*/, '')
    .trim()
}

export function parseLabels(input: string): string[] {
  if (!input) return []

  return Array.from(
    new Set(
      input
        .split(/[\r\n,，;；|、]+/)
        .map((item) => cleanLabel(item))
        .filter(Boolean)
    )
  )
}
