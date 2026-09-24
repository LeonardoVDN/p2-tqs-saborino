<script setup>
import { onMounted, ref } from 'vue'
import api, { clearCsrf } from '@/api/client'
import BrandLogo from '@/components/BrandLogo.vue'
const token = ref('')
const ready = ref(false)
const password = ref('')
const passwordConfirm = ref('')
const error = ref('')
const done = ref(false)
onMounted(() => {
  const params = new URLSearchParams(window.location.hash.slice(1))
  token.value = params.get('token') || ''
  history.replaceState(null, '', window.location.pathname + window.location.search)
})
async function continueReset() {
  error.value = ''
  try { await api.post('/auth/password-reset/exchanges/', { token: token.value }); token.value = ''; ready.value = true }
  catch { token.value = ''; error.value = 'Link inválido, expirado ou já utilizado.' }
}
async function confirmReset() {
  error.value = ''
  if (password.value !== passwordConfirm.value) { error.value = 'As senhas não conferem.'; return }
  try {
    await api.post('/auth/password-reset/confirmations/', { password: password.value })
    // O servidor renova o CSRF ao concluir o reset. A próxima mutação deve
    // obter o valor novo, inclusive no login sem recarregar a página.
    clearCsrf()
    password.value = ''
    passwordConfirm.value = ''
    done.value = true
  }
  catch (response) { error.value = response.response?.data?.password?.[0] || 'Não foi possível redefinir a senha.' }
}
</script>
<template><main class="login"><section class="card login-card"><BrandLogo /><h1>Redefinir senha</h1><p v-if="done" role="status">Senha alterada. Entre novamente com a nova senha.</p><RouterLink v-if="done" class="btn btn-primary" to="/login">Ir para o login</RouterLink><template v-else><p v-if="error" role="alert">{{ error }}</p><p v-if="!token && !ready && !error">Link inválido ou já removido. Abra novamente o link recebido.</p><button v-else-if="!ready" class="btn btn-primary" @click="continueReset">Continuar</button><form v-else @submit.prevent="confirmReset"><label for="new-password">Nova senha</label><input id="new-password" v-model="password" class="input" type="password" minlength="15" maxlength="128" autocomplete="new-password" required><label for="new-password-confirm">Confirmar nova senha</label><input id="new-password-confirm" v-model="passwordConfirm" class="input" type="password" minlength="15" maxlength="128" autocomplete="new-password" required><button class="btn btn-primary" type="submit">Alterar senha</button></form></template></section></main></template>
<style scoped>.login{min-height:100%;display:grid;place-items:center;padding:1.2rem}.login-card{width:100%;max-width:26rem}</style>
