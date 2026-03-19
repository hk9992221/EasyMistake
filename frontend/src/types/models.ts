/**
 * 数据模型类型定义
 * 所有 UUID 字段使用 string 类型
 */

// ==================== 用户相关 ====================
export interface User {
  id: string
  email: string
  username: string
  role: 'USER' | 'ADMIN'
  createdAt: string
  updatedAt: string
}

export interface Invite {
  id: string
  code: string
  createdBy: string
  createdByUser?: User
  maxUses: number
  usedCount: number
  expiresAt: string | null
  createdAt: string
}

// ==================== 图片相关 ====================
export interface Image {
  id: string
  uploadedBy: string
  objectKey: string
  originalFilename: string
  mimeType: string
  sizeBytes: number
  width: number | null
  height: number | null
  s3PresignedUrl?: string
  createdAt: string
  storage_url?: string
}

// ==================== 整卷/资料源 ====================
export interface Paper {
  id: string
  createdBy: string
  qrCode: string | null
  title: string
  paperType: 'exam_paper' | 'textbook' | 'workbook' | 'other'
  subject: string
  bookName: string | null
  grade: string | null
  year: string | null
  semester: string | null
  metadata: Record<string, any>
  createdAt: string
  updatedAt: string
}

// ==================== 识别任务 ====================
export interface Extraction {
  id: string
  createdBy: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  error: string | null
  rawResult: Record<string, any> | null
  createdAt: string
  updatedAt: string
  images?: ExtractionImage[]
}

export interface ExtractionImage {
  extractionId: string
  imageId: string
  imageOrder: number
  image?: Image
}

export interface DraftQuestion {
  // 草稿题目，用于识别结果编辑后入库
  stemText: string
  stemLatex: string | null
  contentJson: Record<string, any> | null
  questionType: string
  options: Record<string, any> | null
  subject: string
  bookName: string | null
  chapterName: string | null
  sectionName: string | null
  pageNo: number | null
  questionNo: string | null
  difficulty: string | null
  tags: string[] | null
  metadata: Record<string, any> | null
}

// ==================== 题目相关 ====================
export interface Question {
  id: string
  user_id: string
  created_by?: string | null
  paper_id: string | null
  subject: string | null
  book_name: string | null
  chapter_name: string | null
  page_no: number | null
  question_no: string | null
  source_anchor: string | null
  type: string
  difficulty: string | null
  stem_text: string | null
  stem_latex: string | null
  content_json: Record<string, any>
  paper_meta: Record<string, any>
  tags_json: string[]
  knowledge_points_json: string[]
  from_extraction_id: string | null
  is_deleted: boolean
  created_at: string
  updated_at: string
  // 兼容字段（用于显示）
  content?: string | null
  content_text?: string | null
  answer_text?: string | null
  appendix?: string | null
  stem_images?: Array<{ image_id: string; order_index: number; url?: string }>
}

// ==================== 答案相关 ====================
export interface AnswerImageItem {
  image_id: string
  order_index: number
  url?: string  // 图片URL，仅在响应时填充
}

export interface Answer {
  id: string
  question_id: string  // 后端使用 question_id 而不是 questionId
  answer_type: 'NONE' | 'TEXT' | 'LATEX' | 'IMAGE' | 'MIXED'
  answer_text: string | null
  answer_latex: string | null
  explanation_text: string | null
  explanation_latex: string | null
  content_json: Record<string, any>
  images: AnswerImageItem[]  // 支持多张答案图片
  from_extraction_id: string | null
  from_api_call_id: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

// 兼容旧代码（前端字段名使用 camelCase）
export interface AnswerLegacy {
  id: string
  questionId: string
  createdBy: string
  answerText: string
  answerLatex: string | null
  explanationText: string | null
  explanationLatex: string | null
  contentJson: Record<string, any> | null
  metadata: Record<string, any> | null
  createdAt: string
  updatedAt: string
}

// ==================== 做题记录 ====================
export interface Attempt {
  id: string
  question_id: string
  user_id: string
  result: 'CORRECT' | 'WRONG' | 'PARTIAL' | 'SKIPPED'
  duration_sec?: number | null
  source?: string | null
  review_mode?: string | null
  error_tags?: string[]
  wrong_reason?: string | null
  note?: string | null
  occurred_at: string
  submitted_at?: string
  created_at?: string
  updated_at?: string
  // legacy fields
  questionId?: string
  userId?: string
  attemptType?: 'practice' | 'exam'
  userAnswer?: Record<string, any>
  isCorrect?: boolean | null
  wrongReasons?: string[] | null
  attemptedAt?: string
}

// ==================== 归档容器 ====================
export interface Submission {
  id: string
  userId: string
  title: string
  description: string | null
  metadata: Record<string, any> | null
  createdAt: string
  updatedAt: string
}

export interface SubmissionItem {
  id: string
  submissionId: string
  questionId: string
  userAnswer: Record<string, any> | null
  isCorrect: boolean | null
  note: string | null
  addedAt: string
  question?: Question
}

// ==================== 组卷相关 ====================
export interface PaperSet {
  id: string
  createdBy: string
  title: string
  description: string | null
  metadata: Record<string, any> | null
  createdAt: string
  updatedAt: string
  subject?: string | null
  output_format?: string | null
  item_count?: number
}

export interface PaperSetItem {
  id: string
  paperSetId: string
  questionId: string
  displayOrder: number
  points: number | null
  note: string | null
  question?: Question
}

// ==================== 导出相关 ====================
export interface Export {
  id: string
  createdBy: string
  paperSetId: string
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'PENDING' | 'RUNNING' | 'DONE' | 'FAILED' | 'PROCESSING' | 'COMPLETED'
  format: 'markdown' | 'latex' | 'pdf' | 'MARKDOWN_ZIP' | 'LATEX_ZIP' | 'PDF'
  error: string | null
  outputObjectKey: string | null
  presignedUrl: string | null
  createdAt: string
  updatedAt: string
  object_key?: string | null
  created_at?: string
}

export interface ExportItem {
  id: string
  exportId: string
  questionId: string
  snapshotContent: Record<string, any>
  answerSnapshotContent: Record<string, any> | null
}

// ==================== 异步任务 ====================
export interface Job {
  id: string
  jobType: 'extraction' | 'answer_generation' | 'export'
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number | null
  result: Record<string, any> | null
  error: string | null
  createdAt: string
  finishedAt: string | null
}

// ==================== API 日志 ====================
export interface ApiCallLog {
  id: string
  userId: string | null
  endpoint: string
  method: string
  statusCode: number
  durationMs: number | null
  requestSize: number | null
  responseSize: number | null
  errorMessage: string | null
  costUsd: number | null
  createdAt: string
}

// ==================== 分页和查询参数 ====================
export interface PaginationParams {
  page?: number
  pageSize?: number
  page_size?: number
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  search?: string
}

export interface QuestionFilters extends PaginationParams {
  subject?: string
  book_name?: string
  chapter_name?: string
  page_no?: number
  question_no?: string
  type?: string
  difficulty?: string
  tags_json?: string[]
  knowledge_point_q?: string
  q?: string
  start_date?: string
  end_date?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize?: number
  page_size?: number
  totalPages?: number
  total_pages?: number
}

export interface QuestionProgress {
  id: string
  user_id: string
  question_id: string
  total_attempts: number
  wrong_attempts: number
  correct_attempts: number
  consecutive_correct: number
  mastery_level: number
  proficiency_score: number
  self_assessment?: string | null
  last_result?: 'CORRECT' | 'WRONG' | 'PARTIAL' | 'SKIPPED' | null
  last_reviewed_at?: string | null
  next_review_at?: string | null
  review_stage: number
  is_mastered: boolean
  created_at: string
  updated_at: string
}

export interface AnalyticsOverview {
  total_questions: number
  mistake_questions: number
  mastered_questions: number
  due_today: number
  overdue: number
  avg_accuracy_7d: number
  avg_accuracy_30d: number
}

export interface ErrorTagStatItem {
  error_tag: string
  count: number
}

export interface ReviewQueueItem {
  question_id: string
  progress_id: string
  priority: number
  reason: string
  review_stage: number
  next_review_at?: string | null
  proficiency_score: number
}

export interface ReviewQueueResponse {
  date: string
  items: ReviewQueueItem[]
}
