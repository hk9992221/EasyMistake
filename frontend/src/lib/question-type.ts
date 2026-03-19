const QUESTION_TYPE_LABEL_MAP: Record<string, string> = {
  MCQ: '选择题',
  FILL_BLANK: '填空题',
  SHORT_ANSWER: '简答题',
  COMPUTATION: '计算题',
  PROOF: '证明题',
  OTHER: '其他',
  SINGLE_CHOICE: '单选题',
  MULTIPLE_CHOICE: '多选题',
}

export function getQuestionTypeLabel(type?: string | null): string {
  if (!type) return '未知题型'
  return QUESTION_TYPE_LABEL_MAP[type] || type
}
