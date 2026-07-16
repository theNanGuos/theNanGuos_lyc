import { expect, test } from '@playwright/test'

test.describe.configure({ mode: 'serial' })

async function previewAndGenerate(page: import('@playwright/test').Page, prompt: string) {
  await page.goto('/create')
  await expect(page.getByLabel('本地保留数量')).toHaveValue('1')
  await page.getByLabel('自然语言创作描述').fill(prompt)
  await page.getByRole('button', { name: '提交描述' }).click()
  await expect(page.getByTestId('plan-genre')).toBeVisible()
  await page.getByTestId('plan-genre').fill('neo soul')
  await page.getByRole('button', { name: '确认方案并生成' }).click()
}

test('创作、等待、成功、播放和下载走完整 Mock 全栈链路', async ({ page }) => {
  await previewAndGenerate(page, 'E2E 主流程：雨夜爵士与钢琴对话')

  await expect(page).toHaveURL(/\/generations\/[a-f0-9]{32}\/result$/)
  await expect(page.getByRole('heading', { name: '歌曲已生成' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'E2E 雨夜对话' })).toBeVisible()

  await page.getByTestId('candidate-play-e2e-audio').click()
  await expect(page.locator('audio')).toHaveAttribute('src', /\/audio\/e2e-audio$/)

  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('link', { name: '下载 MP3' }).first().click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toBe('E2E 雨夜对话.mp3')
})

test('停止等待后可从作品页继续查询', async ({ page }) => {
  await previewAndGenerate(page, 'E2E 停止等待流程')

  await expect(page).toHaveURL(/\/generations\/[a-f0-9]{32}$/)
  await page.getByRole('button', { name: '停止等待' }).click()
  await expect(page.getByText('已停止等待', { exact: true }).first()).toBeVisible()
  await page.getByRole('link', { name: '返回作品列表' }).click()
  await expect(page.getByText('E2E 停止等待流程')).toBeVisible()
  await page.getByRole('button', { name: '继续查询' }).click()

  await expect.poll(async () => {
    await page.reload()
    return page.locator('.work-row').filter({ hasText: 'E2E 停止等待流程' }).textContent()
  }).toContain('已完成')
})

test('服务重启后重新索引的中断任务可从作品页继续查询', async ({ page }) => {
  const seeded = await page.request.post('http://127.0.0.1:18000/__e2e__/seed-interrupted')
  expect(seeded.ok()).toBeTruthy()
  const { request_id: requestId } = await seeded.json()
  expect(requestId).toMatch(/^[a-f0-9]{32}$/)

  await page.goto('/works')
  const row = page.locator('.work-row').filter({ hasText: 'E2E 服务重启恢复流程' })
  await expect(row).toContainText('服务已重启，需继续查询')
  await row.getByRole('button', { name: '继续查询' }).click()

  await expect.poll(async () => {
    await page.reload()
    return page.locator('.work-row').filter({ hasText: 'E2E 服务重启恢复流程' }).textContent()
  }).toContain('已完成')
})

test('保存和清除偏好不会删除作品', async ({ page }) => {
  const before = await page.request.get('/api/generations')
  const beforeCount = (await before.json()).items.length
  expect(beforeCount).toBeGreaterThan(0)

  await page.goto('/preferences')
  await page.getByLabel('默认语言').selectOption('en')
  await page.getByLabel('默认人声').selectOption('m')
  await page.getByRole('button', { name: '保存默认设置' }).click()
  await page.locator('.editor textarea').fill('# E2E preference\n\nPrefer warm piano.')
  await page.getByRole('button', { name: '保存创作偏好' }).click()
  await expect(page.getByText('长期创作偏好已保存')).toBeVisible()
  await page.reload()
  await expect(page.getByLabel('默认语言')).toHaveValue('en')
  await expect(page.locator('.editor textarea')).toHaveValue(/# E2E preference/)

  await page.getByTestId('clear-preferences').click()
  await page.getByRole('dialog').getByRole('button', { name: '确认清除' }).click()
  await expect(page.getByText('偏好已清除，作品未受影响')).toBeVisible()
  await expect(page.getByLabel('默认语言')).toHaveValue('zh')
  await expect(page.locator('.editor textarea')).toHaveValue('')

  const after = await page.request.get('/api/generations')
  expect((await after.json()).items).toHaveLength(beforeCount)
})

test('动态状态、图标控件和键盘焦点均可访问', async ({ page }) => {
  await page.goto('/create')
  const prompt = page.getByLabel('自然语言创作描述')
  await prompt.focus()
  await expect(prompt).toBeFocused()
  expect(await prompt.evaluate(element => getComputedStyle(element).outlineStyle)).toBe('none')
  expect(await prompt.evaluate(element => getComputedStyle(element.parentElement!).boxShadow)).not.toBe('none')

  await page.goto('/generations/demo-c?demo=1')
  await expect(page.getByRole('status')).toHaveAttribute('aria-live', 'polite')

  await page.goto('/generations/demo-a/result?demo=1')
  await expect(page.getByRole('button', { name: /^播放 / }).first()).toBeVisible()
  await expect(page.getByRole('slider', { name: /音量$/ }).first()).toBeVisible()
  const firstVolume = page.getByTestId('candidate-volume-a')
  const secondVolume = page.getByTestId('candidate-volume-b')
  await firstVolume.fill('0.25')
  await secondVolume.fill('0.9')
  await expect(firstVolume).toHaveValue('0.25')
  await expect(secondVolume).toHaveValue('0.9')
  await expect(page.getByTestId('candidate-progress-a')).toHaveAttribute('role', 'slider')

  await page.goto('/works?demo=1')
  await expect(page.getByRole('button', { name: /^播放 / }).first()).toBeVisible()

  await page.goto('/preferences')
  const markdownEditor = page.locator('.editor textarea')
  await markdownEditor.focus()
  await expect(markdownEditor).toBeFocused()
  expect(await markdownEditor.evaluate(element => getComputedStyle(element).outlineStyle)).not.toBe('none')
})

test('作品页进入现有结果页选择版本并永久删除整次任务', async ({ page }) => {
  const prompt = `E2E 删除流程 ${Date.now()}`
  await previewAndGenerate(page, prompt)
  await expect(page).toHaveURL(/\/result$/)

  await page.goto('/works')
  let row = page.locator('.work-row').filter({ hasText: prompt })
  await expect(row).toBeVisible()
  await row.getByTestId('view-versions').click()
  await expect(page).toHaveURL(/\/generations\/[a-f0-9]{32}\/result$/)

  await page.goto('/works')
  row = page.locator('.work-row').filter({ hasText: prompt })
  await row.getByRole('button', { name: /^删除 / }).click()
  await expect(page.getByRole('dialog')).toContainText('不可恢复')
  await page.getByTestId('confirm-delete-generation').click()
  await expect(row).toHaveCount(0)
})
