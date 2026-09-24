import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api, { bootstrapCsrf, clearCsrf } from '@/api/client'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const state = ref('initializing')
  const isAuthenticated = computed(() => state.value === 'authenticated')
  const sessionChannel = typeof BroadcastChannel === 'function' ? new BroadcastChannel('saborino-session-v1') : null

  if (sessionChannel) {
    sessionChannel.onmessage = (event) => {
      if (event.data?.type !== 'logout' || state.value !== 'authenticated') return
      clearCsrf()
      user.value = null
      state.value = 'anonymous'
      window.location.replace('/login')
    }
  }

  async function initialize() {
    if (state.value !== 'initializing') return
    await bootstrapCsrf()
    await carregarUsuario()
  }

  async function login(email, password) {
    try {
      await api.post('/auth/sessions/', { email, password })
      clearCsrf()
      await bootstrapCsrf()
      await carregarUsuario()
      return { success: true }
    } catch (e) {
      state.value = 'anonymous'
      const status = e.response?.status
      const error = status === 401
        ? 'E-mail ou senha inválidos.'
        : status === 429
          ? 'Muitas tentativas. Aguarde alguns minutos e tente novamente.'
          : status === 403
            ? 'A proteção da sessão foi renovada. Tente entrar novamente.'
            : 'Não foi possível conectar ao sistema. Tente novamente em instantes.'
      return { success: false, error }
    }
  }

  async function carregarUsuario() {
    try {
      const { data } = await api.get('/me/')
      user.value = data
      state.value = 'authenticated'
    } catch (e) {
      user.value = null
      state.value = 'anonymous'
    }
  }

  async function logout() {
    try {
      await api.delete('/auth/session/')
    } finally {
      clearCsrf()
      user.value = null
      state.value = 'anonymous'
      sessionChannel?.postMessage({ type: 'logout' })
      await bootstrapCsrf()
    }
  }

  return { user, state, isAuthenticated, initialize, login, logout, carregarUsuario }
})
