<script setup>
import { ref } from 'vue'
import api from '@/api/client'
import { useAuthStore } from '@/stores/auth'
const auth = useAuthStore()
const revokePassword = ref('')
const currentPassword = ref('')
const newPassword = ref('')
const passwordConfirm = ref('')
const emailPassword = ref('')
const newEmail = ref('')
const error = ref('')
const message = ref('')
async function revokeAll() {
  error.value = ''; message.value = ''
  try { await api.post('/auth/sessions/revoke-all/', { password: revokePassword.value }); await auth.logout() }
  catch { error.value = 'Não foi possível encerrar as sessões.' }
}
async function changePassword() {
  error.value = ''; message.value = ''
  if (newPassword.value !== passwordConfirm.value) { error.value = 'As senhas não conferem.'; return }
  try {
    await api.post('/auth/password/changes/', { current_password: currentPassword.value, new_password: newPassword.value })
    await auth.logout()
  } catch (response) { error.value = response.response?.data?.password?.[0] || response.response?.data?.detail || 'Não foi possível alterar a senha.' }
}
async function requestEmailChange() {
  error.value = ''; message.value = ''
  try {
    await api.post('/auth/email-change/requests/', { current_password: emailPassword.value, new_email: newEmail.value })
    message.value = 'Enviamos a confirmação para o novo endereço. Seu e-mail atual permanece válido até a confirmação.'
  } catch (response) { error.value = response.response?.data?.new_email?.[0] || response.response?.data?.detail || 'Não foi possível solicitar a troca.' }
}
</script>
<template><section class="card security"><h1>Segurança da conta</h1><p v-if="error" role="alert">{{ error }}</p><p v-if="message" role="status">{{ message }}</p><form @submit.prevent="changePassword"><h2>Alterar senha</h2><label for="password-current">Senha atual</label><input id="password-current" v-model="currentPassword" class="input" type="password" autocomplete="current-password" required><label for="password-new">Nova senha</label><input id="password-new" v-model="newPassword" class="input" type="password" minlength="15" maxlength="128" autocomplete="new-password" required><label for="password-confirm">Confirmar nova senha</label><input id="password-confirm" v-model="passwordConfirm" class="input" type="password" minlength="15" maxlength="128" autocomplete="new-password" required><button class="btn btn-primary">Alterar senha</button></form><form @submit.prevent="requestEmailChange"><h2>Alterar e-mail</h2><label for="email-new">Novo e-mail</label><input id="email-new" v-model="newEmail" class="input" type="email" autocomplete="email" required><label for="email-password">Senha atual</label><input id="email-password" v-model="emailPassword" class="input" type="password" autocomplete="current-password" required><button class="btn btn-primary">Enviar confirmação</button></form><form @submit.prevent="revokeAll"><h2>Encerrar todas as sessões</h2><label for="revoke-password">Senha atual</label><input id="revoke-password" v-model="revokePassword" class="input" type="password" autocomplete="current-password" required><button class="btn btn-primary">Encerrar todas</button></form></section></template>
<style scoped>.security{max-width:36rem;display:grid;gap:.7rem}</style>
