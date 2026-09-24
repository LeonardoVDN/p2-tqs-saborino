<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import BrandLogo from '@/components/BrandLogo.vue'

const auth = useAuthStore()
const router = useRouter()
const email = ref('')
const password = ref('')
const erro = ref('')
const carregando = ref(false)

async function entrar() {
  erro.value = ''
  carregando.value = true
  const r = await auth.login(email.value, password.value)
  carregando.value = false
  if (r.success) router.push('/')
  else erro.value = r.error
}
</script>

<template>
  <div class="login">
    <form class="card login-card" @submit.prevent="entrar">
      <BrandLogo />
      <p class="sub">Gestão de doces em pote</p>
      <div class="field">
        <label for="email">E-mail</label>
        <input id="email" class="input" v-model="email" type="email" autocomplete="username" autofocus required />
      </div>
      <div class="field">
        <label for="password">Senha</label>
        <input id="password" class="input" type="password" v-model="password" autocomplete="current-password" required />
      </div>
      <p v-if="erro" class="erro">{{ erro }}</p>
      <button class="btn btn-primary btn-block" :disabled="carregando">
        {{ carregando ? 'Entrando…' : 'Entrar' }}
      </button>
      <RouterLink class="forgot" to="/esqueci-senha">Esqueci minha senha</RouterLink>
      <RouterLink class="forgot" to="/reenviar-confirmacao">Reenviar confirmação de e-mail</RouterLink>
    </form>
  </div>
</template>

<style scoped>
.login { min-height: 100%; display: grid; place-items: center; padding: 1.2rem; }
.login-card { width: 100%; max-width: 22rem; }
.sub { color: var(--muted); margin: .2rem 0 1.2rem; }
.erro { color: var(--crit); font-size: .88rem; margin: 0 0 .7rem; }
.forgot { display: block; margin-top: .9rem; text-align: center; }
</style>
