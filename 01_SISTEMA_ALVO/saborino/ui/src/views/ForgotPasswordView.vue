<script setup>
import { ref } from 'vue'
import api from '@/api/client'
import BrandLogo from '@/components/BrandLogo.vue'
const email = ref('')
const sent = ref(false)
const loading = ref(false)
async function submit() {
  loading.value = true
  try { await api.post('/auth/password-reset/requests/', { email: email.value }) } finally {
    loading.value = false
    sent.value = true
  }
}
</script>
<template>
  <main class="login"><form class="card login-card" @submit.prevent="submit">
    <BrandLogo />
    <h1>Recuperar senha</h1>
    <p v-if="sent" role="status">Se existir uma conta elegível, enviaremos as instruções.</p>
    <template v-else><label for="forgot-email">E-mail</label><input id="forgot-email" v-model="email" class="input" type="email" autocomplete="email" required autofocus><button class="btn btn-primary btn-block" :disabled="loading">{{ loading ? 'Enviando…' : 'Enviar instruções' }}</button></template>
    <RouterLink to="/login">Voltar ao login</RouterLink>
  </form></main>
</template>
<style scoped>.login{min-height:100%;display:grid;place-items:center;padding:1.2rem}.login-card{width:100%;max-width:26rem;display:grid;gap:.8rem}</style>
