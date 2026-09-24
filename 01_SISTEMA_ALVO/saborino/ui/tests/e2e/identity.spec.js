import { expect, test } from '@playwright/test'


async function mockAnonymousApi(page, onRequest = () => {}) {
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    onRequest(request)
    const pathname = new URL(request.url()).pathname
    if (pathname.endsWith('/auth/csrf/')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ csrfToken: 'masked-test-csrf' }) })
    }
    if (pathname.endsWith('/me/')) {
      return route.fulfill({ status: 401, contentType: 'application/json', body: '{}' })
    }
    return route.fulfill({ status: 204, body: '' })
  })
}


test('remove apenas tokens legados e preserva storage alheio', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('saborino_access', 'legacy-access')
    localStorage.setItem('saborino_refresh', 'legacy-refresh')
    localStorage.setItem('preferencia_visual', 'compacta')
  })
  await mockAnonymousApi(page)
  await page.goto('/login')
  await expect(page.getByRole('button', { name: 'Entrar' })).toBeVisible()
  const storage = await page.evaluate(() => Object.fromEntries(Object.entries(localStorage)))
  expect(storage.saborino_access).toBeUndefined()
  expect(storage.saborino_refresh).toBeUndefined()
  expect(storage.preferencia_visual).toBe('compacta')
  await expect(page).toHaveTitle('Saborino')
  await expect(page.locator('html')).toHaveAttribute('lang', 'pt-BR')
  await expect(page.locator('link[rel="icon"]')).toHaveAttribute('href', '/saborino-logo.png')
  await expect(page.getByRole('img', { name: 'Doceria Saborino' })).toBeVisible()
})

test('login após reset usa CSRF renovado sem recarregar nem repetir POST', async ({ page }) => {
  let csrf = 'csrf-before-reset'
  let loginPosts = 0
  let loginStatus = null
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    if (path.endsWith('/auth/csrf/')) return route.fulfill({ status: 200, json: { csrfToken: csrf } })
    if (path.endsWith('/me/')) return route.fulfill({ status: 401, json: {} })
    if (path.endsWith('/password-reset/confirmations/')) {
      expect(request.headers()['x-csrftoken']).toBe(csrf)
      csrf = 'csrf-after-reset'
    }
    if (path.endsWith('/auth/sessions/')) {
      loginPosts++
      loginStatus = request.headers()['x-csrftoken'] === csrf ? 401 : 403
      // Credenciais sintéticas deliberadamente inválidas: testa o CSRF antes
      // da autenticação, sem depender das APIs comerciais do dashboard.
      return route.fulfill({ status: loginStatus, json: {} })
    }
    return route.fulfill({ status: 204 })
  })
  await page.goto('/redefinir-senha#token=synthetic-reset-token')
  await page.getByRole('button', { name: 'Continuar' }).click()
  await page.getByLabel('Nova senha', { exact: true }).fill('senha sintetica de teste 2026')
  await page.getByLabel('Confirmar nova senha').fill('senha sintetica de teste 2026')
  await page.getByRole('button', { name: 'Alterar senha' }).click()
  await page.getByRole('link', { name: 'Ir para o login' }).click()
  await page.getByLabel('E-mail', { exact: true }).fill('owner@example.com')
  await page.getByLabel('Senha', { exact: true }).fill('senha sintetica de teste 2026')
  await page.getByRole('button', { name: 'Entrar', exact: true }).click()
  await expect(page.getByText('E-mail ou senha inválidos.', { exact: true })).toBeVisible()
  expect(loginStatus).toBe(401)
  expect(loginPosts).toBe(1)
})

test('logo original permanece legível e sem distorção nas telas públicas no celular', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 })
  await mockAnonymousApi(page)
  for (const path of ['/login', '/esqueci-senha', '/reenviar-confirmacao', '/confirmar-email', '/redefinir-senha']) {
    await page.goto(path)
    const logo = page.getByRole('img', { name: 'Doceria Saborino' })
    await expect(logo).toBeVisible()
    await expect(logo).toHaveAttribute('src', '/saborino-logo.png')
    await expect.poll(() => logo.evaluate(image => image.complete && image.naturalWidth > 0)).toBe(true)
    const bounds = await logo.boundingBox()
    expect(bounds.width).toBeLessThanOrEqual(192)
    expect(bounds.width / bounds.height).toBeCloseTo(1136 / 1132, 2)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  }
})

test('login não apresenta erro de CSRF como senha inválida', async ({ page }) => {
  await mockAnonymousApi(page)
  await page.route('**/api/v1/auth/sessions/', route => route.fulfill({ status: 403, json: {} }))
  await page.goto('/login')
  await page.getByLabel('E-mail', { exact: true }).fill('owner@example.com')
  await page.getByLabel('Senha', { exact: true }).fill('senha sintetica de teste 2026')
  await page.getByRole('button', { name: 'Entrar', exact: true }).click()
  await expect(page.getByText('A proteção da sessão foi renovada. Tente entrar novamente.')).toBeVisible()
})


test('reset limpa fragmento antes do exchange e não consome no GET', async ({ page }) => {
  const requests = []
  await mockAnonymousApi(page, (request) => requests.push({ method: request.method(), url: request.url(), data: request.postDataJSON?.() }))
  await page.goto('/redefinir-senha#token=opaque-reset-token')
  await expect(page).toHaveURL('http://127.0.0.1:4189/redefinir-senha')
  expect(requests.some(({ url }) => url.includes('/password-reset/exchanges/'))).toBeFalsy()
  await page.getByRole('button', { name: 'Continuar' }).click()
  await expect(page.getByLabel('Nova senha', { exact: true })).toBeVisible()
  const exchange = requests.find(({ url }) => url.includes('/password-reset/exchanges/'))
  expect(exchange.data).toEqual({ token: 'opaque-reset-token' })
  await page.getByLabel('Nova senha', { exact: true }).fill('senha nova de navegador 2026')
  await page.getByLabel('Confirmar nova senha').fill('senha nova de navegador 2026')
  await page.getByRole('button', { name: 'Alterar senha' }).click()
  await expect(page.getByText('Senha alterada. Entre novamente com a nova senha.')).toBeVisible()
})


test('confirmação de e-mail mantém finalidade e limpa fragmento', async ({ page }) => {
  const requests = []
  await mockAnonymousApi(page, (request) => requests.push({ url: request.url(), data: request.postDataJSON?.() }))
  await page.goto('/confirmar-email#purpose=change&token=opaque-email-token')
  await expect(page).toHaveURL('http://127.0.0.1:4189/confirmar-email')
  expect(requests.some(({ url }) => url.includes('/email-change/confirmations/'))).toBeFalsy()
  await page.getByRole('button', { name: 'Confirmar e-mail' }).click()
  await expect(page.getByText('E-mail confirmado. Entre novamente para continuar.')).toBeVisible()
  const confirmation = requests.find(({ url }) => url.includes('/email-change/confirmations/'))
  expect(confirmation.data).toEqual({ token: 'opaque-email-token' })
})


test('deep link autenticado é retomado pela sessão sem bearer', async ({ page }) => {
  const requests = []
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    requests.push(request)
    const pathname = new URL(request.url()).pathname
    if (pathname.endsWith('/auth/csrf/')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ csrfToken: 'masked-test-csrf' }) })
    if (pathname.endsWith('/me/')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: 7, username: 'owner', email: 'owner@example.com' }) })
    if (pathname.endsWith('/competencias/atual/')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: 1, rotulo: 'Setembro/2026' }) })
    if (pathname.endsWith('/competencias/')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([{ id: 1, rotulo: 'Setembro/2026' }]) })
    return route.fulfill({ status: 404, contentType: 'application/json', body: '{}' })
  })
  await page.goto('/conta/seguranca')
  await expect(page.getByRole('heading', { name: 'Segurança da conta' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Saborino — início' }).getByRole('img')).toBeVisible()
  expect(requests.some((request) => request.headers().authorization)).toBeFalsy()
})


test('logout é propagado para outra aba sem gravar credencial', async ({ context }) => {
  let loggedIn = true
  await context.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const pathname = new URL(request.url()).pathname
    if (pathname.endsWith('/auth/csrf/')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ csrfToken: 'masked-test-csrf' }) })
    if (pathname.endsWith('/me/')) return route.fulfill({ status: loggedIn ? 200 : 401, contentType: 'application/json', body: loggedIn ? JSON.stringify({ id: 7, username: 'owner', email: 'owner@example.com' }) : '{}' })
    if (pathname.endsWith('/auth/session/') && request.method() === 'DELETE') { loggedIn = false; return route.fulfill({ status: 204 }) }
    if (pathname.endsWith('/competencias/atual/')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: 1, rotulo: 'Setembro/2026' }) })
    if (pathname.endsWith('/competencias/')) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([{ id: 1, rotulo: 'Setembro/2026' }]) })
    return route.fulfill({ status: 404, contentType: 'application/json', body: '{}' })
  })
  const first = await context.newPage()
  const second = await context.newPage()
  await Promise.all([first.goto('/'), second.goto('/conta/seguranca')])
  await expect(second.getByRole('heading', { name: 'Segurança da conta' })).toBeVisible()
  await first.getByRole('button', { name: /owner/ }).click()
  await expect(second).toHaveURL('http://127.0.0.1:4189/login')
  const credentialKeys = await second.evaluate(() => Object.keys(localStorage).filter((key) => /access|refresh|token/i.test(key)))
  expect(credentialKeys).toEqual([])
})
