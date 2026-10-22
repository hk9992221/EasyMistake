import { expect, test, type Page, type Route } from '@playwright/test'

const alpha = { id: '11111111-1111-4111-8111-111111111111', email: 'alpha@example.com', role: 'USER', username: 'alpha' }
const beta = { id: '22222222-2222-4222-8222-222222222222', email: 'beta@example.com', role: 'USER', username: 'beta' }
const imageId = '33333333-3333-4333-8333-333333333333'
const qid = '44444444-4444-4444-8444-444444444444'
const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=', 'base64')
const question = (name = 'Alpha private question') => ({
  id: qid, user_id: alpha.id, type: 'COMPUTATION', subject: '数学', stem_text: name,
  stem_latex: null, content_json: {}, paper_meta: {}, tags_json: [], knowledge_points_json: [],
  stem_images: [], is_deleted: false, created_at: '2026-10-23T00:00:00Z', updated_at: '2026-10-23T00:00:00Z',
})
const paginated = (items: unknown[]) => ({ items, total: items.length, page: 1, page_size: 20, total_pages: items.length ? 1 : 0 })

async function setup(page: Page) {
  await page.addInitScript((user) => {
    if (sessionStorage.getItem('e2e-auth-initialized')) return
    sessionStorage.setItem('e2e-auth-initialized', '1')
    localStorage.setItem('auth-storage', JSON.stringify({ state: { user, token: 'token-alpha', isAuthenticated: true }, version: 0 }))
  }, alpha)
  page.on('dialog', (dialog) => dialog.accept())
  const state = { uploads: 0, saves: [] as any[], answerUpdates: [] as any[], restored: false, failFirstSave: false,
    betaListRequested: false, holdBetaList: null as Promise<void> | null,
    oldCostRequest: null as Route | null, holdOldCost: false }
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname.replace('/api/v1', '')
    const user = request.headers().authorization === 'Bearer token-beta' ? beta : alpha
    const json = (body: unknown, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
    if (path === '/auth/login') {
      const next = new URLSearchParams(request.postData() || '').get('username') === beta.email ? beta : alpha
      return json({ user: next, access_token: next === beta ? 'token-beta' : 'token-alpha', token_type: 'bearer' })
    }
    if (path === '/auth/logout') return json({})
    if (path === '/auth/me') return json(user)
    if (path === '/auth/me/dashboard' && user === alpha && state.holdOldCost) {
      state.oldCostRequest = route
      return
    }
    if (path === '/auth/me/dashboard') return json({ total_cost_usd: 0, calls_by_date: {}, calls_by_model: {}, calls_by_purpose: {} })
    if (path === '/questions/user/common-tags') return json({ tags: [] })
    if (path === '/questions/with-answer') {
      state.saves.push(request.postDataJSON())
      if (state.failFirstSave && state.saves.length === 1) return route.abort('connectionreset')
      return json(question(), 201)
    }
    if (path === '/questions/trash') return json(paginated(state.restored ? [] : [question('Recover me')]))
    if (path.endsWith('/restore')) { state.restored = true; return json(question()) }
    if (path === '/questions' || path === '/questions/') {
      if (user === beta && url.searchParams.get('page_size') === '20') {
        state.betaListRequested = true
        if (state.holdBetaList) await state.holdBetaList
      }
      return json(paginated([question(user === alpha ? 'Alpha private question' : 'Beta private question')]))
    }
    if (path === `/questions/${qid}`) return json(question())
    if (path === `/questions/${qid}/answer`) {
      if (request.method() === 'PUT') state.answerUpdates.push(request.postDataJSON())
      const updated = state.answerUpdates.at(-1) ?? { answer_text: 'Original answer', answer_type: 'MIXED' }
      return json({ question_id: qid, ...updated, images: [{ image_id: imageId, order_index: 0 }] })
    }
    if (path.includes('attempts')) return json([])
    if (path === '/images/upload') {
      state.uploads++
      return json({ id: imageId, mime: 'image/png' }, 201)
    }
    if (path === `/images/${imageId}/file`) {
      expect(request.headers().authorization).toBe('Bearer token-alpha')
      expect(url.searchParams.has('token')).toBe(false)
      return route.fulfill({ contentType: 'image/png', body: png })
    }
    if (path.startsWith('/reviews')) return json({ ...paginated([]), due_count: 0 })
    if (path === '/analytics/overview') return json({ total_questions: 1, unmastered_wrong_questions: 0 })
    if (path === '/analytics/error-tags') return json({ items: [] })
    if (path.startsWith('/question-progress')) return json(paginated([]))
    throw new Error(`Unexpected API request: ${request.method()} ${path}`)
  })
  return state
}

async function loginAs(page: Page, email: string) {
  await page.getByRole('button', { name: '退出登录', exact: true }).click()
  await expect(page).toHaveURL(/\/login$/)
  await page.getByLabel('邮箱', { exact: true }).fill(email)
  await page.getByLabel('密码', { exact: true }).fill('password123')
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
}

test('draft reload preserves images and the save retry ID; successful save clears it', async ({ page }) => {
  const state = await setup(page)
  state.failFirstSave = true
  await page.goto('/dashboard/extract')
  await page.getByLabel('学科 *', { exact: true }).fill('数学')
  await page.getByRole('combobox', { name: '题型 *' }).click()
  await page.getByRole('option', { name: '计算题', exact: true }).click()
  await page.getByLabel('题干文本', { exact: true }).fill('A draft worth recovering')
  await page.getByLabel('答案文本', { exact: true }).fill('42')
  await page.locator('#stem-image-input').setInputFiles({ name: 'draft.png', mimeType: 'image/png', buffer: png })
  await expect(page.getByAltText('stem-1')).toBeVisible()
  await expect(page.getByText('草稿已自动保存，刷新后可恢复文字和图片')).toBeVisible()
  await page.getByRole('button', { name: '保存试题', exact: true }).click()
  await expect(page.getByText('提交失败', { exact: true })).toBeVisible()
  await page.reload()
  await expect(page.getByLabel('题干文本', { exact: true })).toHaveValue('A draft worth recovering')
  await expect(page.getByLabel('答案文本', { exact: true })).toHaveValue('42')
  await expect(page.getByAltText('stem-1')).toBeVisible()
  await page.getByRole('button', { name: '保存试题', exact: true }).click()
  await expect(page).toHaveURL(/\/dashboard\/questions$/)
  expect(state.uploads).toBe(1)
  expect(state.saves).toHaveLength(2)
  expect(state.saves[1]).toEqual(state.saves[0])
  await page.getByRole('link', { name: '录入试题', exact: true }).first().click()
  await expect(page.getByLabel('题干文本', { exact: true })).toHaveValue('')
  await expect(page.getByAltText('stem-1')).toHaveCount(0)
})

test('account switch clears cached questions and ignores a late 401 from the old session', async ({ page }) => {
  const state = await setup(page)
  state.holdOldCost = true
  await page.goto('/dashboard')
  await expect.poll(() => Boolean(state.oldCostRequest)).toBe(true)
  await page.getByRole('link', { name: '试题', exact: true }).click()
  await expect(page.getByText('Alpha private question', { exact: true })).toBeVisible()
  let releaseList!: () => void
  state.holdBetaList = new Promise((resolve) => { releaseList = resolve })
  await loginAs(page, beta.email)
  await state.oldCostRequest!.fulfill({ status: 401, contentType: 'application/json', body: '{"message":"expired"}' })
  await page.getByRole('link', { name: '试题', exact: true }).click()
  await expect.poll(() => state.betaListRequested).toBe(true)
  await expect(page.getByText('Alpha private question', { exact: true })).toHaveCount(0)
  releaseList()
  await expect(page.getByText('Beta private question', { exact: true })).toBeVisible()
  await expect(page).toHaveURL(/\/dashboard\/questions$/)
})

test('drafts are isolated by account and survive logging out', async ({ page }) => {
  await setup(page)
  await page.goto('/dashboard/extract')
  await page.getByLabel('题干文本', { exact: true }).fill('Only alpha should restore this')
  await expect(page.getByText('草稿已自动保存，刷新后可恢复文字和图片')).toBeVisible()
  await loginAs(page, beta.email)
  await page.getByRole('link', { name: '录入试题', exact: true }).first().click()
  await expect(page.getByLabel('题干文本', { exact: true })).toHaveValue('')
  await page.getByLabel('题干文本', { exact: true }).fill('Beta draft')
  await expect(page.getByText('草稿已自动保存，刷新后可恢复文字和图片')).toBeVisible()
  await loginAs(page, alpha.email)
  await page.getByRole('link', { name: '录入试题', exact: true }).first().click()
  await expect(page.getByLabel('题干文本', { exact: true })).toHaveValue('Only alpha should restore this')
})

for (const [text, type] of [['Changed answer', 'MIXED'], ['', 'IMAGE']]) {
  test(`editing an answer with an image preserves ${type}`, async ({ page }) => {
    const state = await setup(page)
    await page.goto(`/dashboard/questions/${qid}`)
    const answer = page.getByRole('region', { name: '答案', exact: true })
    await answer.getByRole('button', { name: '显示', exact: true }).click()
    await answer.getByRole('button', { name: '编辑', exact: true }).click()
    await answer.getByPlaceholder('编辑答案...').fill(text)
    await answer.getByRole('button', { name: '保存', exact: true }).click()
    await expect.poll(() => state.answerUpdates.length).toBe(1)
    expect(state.answerUpdates[0].answer_type).toBe(type)
  })
}

test('trash restores a question and refreshes the empty state', async ({ page }) => {
  const state = await setup(page)
  await page.goto('/dashboard/trash')
  await expect(page.getByText('Recover me', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: '恢复', exact: true }).click()
  await expect(page.getByText('暂无已删除的题目')).toBeVisible()
  expect(state.restored).toBe(true)
})
