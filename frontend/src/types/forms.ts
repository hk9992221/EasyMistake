/**
 * 表单数据类型定义
 */

import { z } from 'zod'

// ==================== 认证相关表单 ====================
export const loginSchema = z.object({
  email: z.string().email('请输入有效的邮箱地址'),
  password: z.string().min(6, '密码至少6个字符'),
})

export type LoginFormValues = z.infer<typeof loginSchema>

export const registerSchema = z.object({
  username: z.string().min(2, '用户名至少2个字符').max(50, '用户名最多50个字符'),
  email: z.string().email('请输入有效的邮箱地址'),
  password: z.string().min(6, '密码至少6个字符'),
  confirmPassword: z.string(),
  inviteCode: z.string().min(1, '请输入邀请码'),
}).refine((data) => data.password === data.confirmPassword, {
  message: '两次密码输入不一致',
  path: ['confirmPassword'],
})

export type RegisterFormValues = z.infer<typeof registerSchema>

// ==================== 题目相关表单 ====================
export const questionSchema = z.object({
  stemText: z.string().min(1, '请输入题干内容'),
  stemLatex: z.string().optional(),
  contentJson: z.any().optional(),
  questionType: z.enum(['multiple_choice', 'fill_blank', 'short_answer', 'essay', 'calculation'], {
    required_error: '请选择题型',
  }),
  options: z.any().optional(),
  subject: z.string().min(1, '请选择学科'),
  bookName: z.string().optional(),
  chapterName: z.string().optional(),
  sectionName: z.string().optional(),
  pageNo: z.number().optional().nullable(),
  questionNo: z.string().optional(),
  difficulty: z.enum(['easy', 'medium', 'hard']).optional().nullable(),
  tags: z.array(z.string()).optional(),
  metadata: z.any().optional(),
})

export type QuestionFormValues = z.infer<typeof questionSchema>

// ==================== 答案相关表单 ====================
export const answerSchema = z.object({
  answerText: z.string().min(1, '请输入答案内容'),
  answerLatex: z.string().optional(),
  explanationText: z.string().optional(),
  explanationLatex: z.string().optional(),
  contentJson: z.any().optional(),
  metadata: z.any().optional(),
})

export type AnswerFormValues = z.infer<typeof answerSchema>

// ==================== 整卷相关表单 ====================
export const paperSchema = z.object({
  qrCode: z.string().optional(),
  title: z.string().min(1, '请输入标题'),
  paperType: z.enum(['exam_paper', 'textbook', 'workbook', 'other'], {
    required_error: '请选择类型',
  }),
  subject: z.string().min(1, '请选择学科'),
  bookName: z.string().optional(),
  grade: z.string().optional(),
  year: z.string().optional(),
  semester: z.string().optional(),
  metadata: z.any().optional(),
})

export type PaperFormValues = z.infer<typeof paperSchema>

// ==================== 组卷相关表单 ====================
export const paperSetSchema = z.object({
  title: z.string().min(1, '请输入组卷标题'),
  description: z.string().optional(),
  metadata: z.any().optional(),
})

export type PaperSetFormValues = z.infer<typeof paperSetSchema>

export const paperSetItemSchema = z.object({
  questionId: z.string().min(1, '请选择题目'),
  displayOrder: z.number().optional(),
  points: z.number().optional().nullable(),
  note: z.string().optional(),
})

export type PaperSetItemFormValues = z.infer<typeof paperSetItemSchema>

// ==================== 导出相关表单 ====================
export const exportSchema = z.object({
  paperSetId: z.string().min(1, '请选择组卷'),
  format: z.enum(['markdown', 'latex', 'pdf'], {
    required_error: '请选择导出格式',
  }),
})

export type ExportFormValues = z.infer<typeof exportSchema>

// ==================== 归档容器相关表单 ====================
export const submissionSchema = z.object({
  title: z.string().min(1, '请输入标题'),
  description: z.string().optional(),
  metadata: z.any().optional(),
})

export type SubmissionFormValues = z.infer<typeof submissionSchema>

// ==================== 做题记录相关表单 ====================
export const attemptSchema = z.object({
  questionId: z.string().min(1, '请选择题目'),
  attemptType: z.enum(['practice', 'exam'], {
    required_error: '请选择做题类型',
  }),
  userAnswer: z.any().optional(),
})

export type AttemptFormValues = z.infer<typeof attemptSchema>
