<script setup>
import { onMounted, ref } from 'vue'
import api from '@/api/client'
import BrandLogo from '@/components/BrandLogo.vue'

const token = ref('')
const purpose = ref('')
const error = ref('')
const done = ref(false)
const loading = ref(false)

onMounted(() => {
  const params = new URLSearchParams(window.location.hash.slice(1))
  token.value = params.get('token') || ''
  purpose.value = params.get('purpose') || ''
  history.replaceState(null, '', window.location.pathname + window.location.search)
})

async function confirm() {
  error.value = ''
  loading.value = true
  const path = purpose.value === 'verification'
    ? '/auth/email-verification/confirmations/'
    : purpose.value === 'change' ? '/auth/email-change/confirmations/' : ''
  if (!path || !token.value) {
    error.value = 'Link inválido ou incompleto.'
    loading.value = false
    return
  }
  try {
    await api.post(path, { token: token.value })
    token.value = ''
    done.value = true
  } catch {
    token.value = ''
    error.value = 'Link inválido, expirado ou já utilizado.'
  } finally {
    loading.value = false
  }
}
</script>
<template><main class="login"><section class="card confirm-card"><BrandLogo /><h1>Confirmar e-mail</h1><p v-if="done" role="status">E-mail confirmado. Entre novamente para continuar.</p><RouterLink v-if="done" class="btn btn-primary" to="/login">Ir para o login</RouterLink><template v-else><p v-if="error" role="alert">{{ error }}</p><p v-if="!token && !error">Link inválido ou já removido. Abra novamente o link recebido.</p><button v-else class="btn btn-primary" :disabled="loading" @click="confirm">{{ loading ? 'Confirmando…' : 'Confirmar e-mail' }}</button></template></section></main></template>
<style scoped>.login{min-height:100%;display:grid;place-items:center;padding:1.2rem}.card{max-width:28rem}</style>
