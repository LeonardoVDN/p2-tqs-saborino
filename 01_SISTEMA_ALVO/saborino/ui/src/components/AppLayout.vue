<script setup>
import { computed, onMounted } from 'vue'
import { useRouter, RouterLink, RouterView } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCompetenciaStore } from '@/stores/competencia'
import AppToast from '@/components/AppToast.vue'
import BrandLogo from '@/components/BrandLogo.vue'

const auth = useAuthStore()
const comp = useCompetenciaStore()
const router = useRouter()

const nav = [
  { to: '/', label: 'Painel', icon: '📊' },
  { to: '/venda', label: 'Nova venda', icon: '➕' },
  { to: '/vendas', label: 'Vendas', icon: '🧾' },
  { to: '/a-receber', label: 'A receber', icon: '💰' },
  { to: '/produtos', label: 'Produtos', icon: '🧁' },
  { to: '/clientes', label: 'Clientes', icon: '👥' },
  { to: '/compras', label: 'Compras', icon: '🛒' },
  { to: '/producao', label: 'Produção', icon: '🍳' },
  { to: '/fechamento', label: 'Fechamento', icon: '📆' },
  { to: '/config', label: 'Config', icon: '⚙️' },
  { to: '/conta/seguranca', label: 'Segurança', icon: '🔐' },
]

const usuario = computed(() => auth.user?.username || 'sócio')

async function sair() {
  await auth.logout()
  router.push('/login')
}

onMounted(() => {
  if (!comp.atual) comp.inicializar()
  if (!auth.user) auth.carregarUsuario()
})
</script>

<template>
  <div class="shell">
    <header class="topbar">
      <RouterLink class="brand" to="/" aria-label="Saborino — início"><BrandLogo compact /></RouterLink>
      <div class="spacer"></div>
      <label class="comp">
        <span class="comp-label">Competência</span>
        <select class="select comp-select" :value="comp.atual?.id"
                @change="comp.selecionar($event.target.value)">
          <option v-for="c in comp.lista" :key="c.id" :value="c.id">{{ c.rotulo }}</option>
        </select>
      </label>
      <button class="btn btn-sm btn-ghost user" @click="sair" :title="'Sair (' + usuario + ')'">
        <span class="who">{{ usuario }}</span> ⏻
      </button>
    </header>

    <nav class="tabs">
      <RouterLink v-for="n in nav" :key="n.to" :to="n.to" class="tab" active-class="active"
                  :class="{ cta: n.to === '/venda' }">
        <span class="ico">{{ n.icon }}</span><span class="lbl">{{ n.label }}</span>
      </RouterLink>
    </nav>

    <main class="content">
      <RouterView />
    </main>
    <AppToast />
  </div>
</template>

<style scoped>
.shell { min-height: 100%; display: flex; flex-direction: column; }
.topbar {
  display: flex; align-items: center; gap: .7rem; padding: .5rem 1rem; height: 6rem;
  background: var(--surface); border-bottom: 1px solid var(--hairline);
  position: sticky; top: 0; z-index: 20;
}
.brand { display: block; flex-shrink: 0; }
.comp { display: flex; flex-direction: column; align-items: flex-end; gap: .1rem; }
.comp-label { font-size: .64rem; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); }
.comp-select { min-height: 34px; padding: .2rem .5rem; font-weight: 600; }
.user { gap: .3rem; }
.who { max-width: 9ch; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tabs {
  display: flex; gap: .3rem; padding: .5rem 1rem; overflow-x: auto;
  background: var(--surface); border-bottom: 1px solid var(--hairline);
  position: sticky; top: 6rem; z-index: 15; -webkit-overflow-scrolling: touch;
}
.tab {
  display: inline-flex; align-items: center; gap: .35rem; padding: .4rem .7rem;
  border-radius: 999px; white-space: nowrap; color: var(--ink-soft); font-weight: 600;
  font-size: .88rem; border: 1px solid transparent;
}
.tab .ico { font-size: 1rem; }
.tab.active { background: var(--accent-soft); color: var(--accent-ink); }
.tab.cta { background: var(--accent); color: #fff; }
.tab.cta.active { background: var(--accent-ink); }
.content { flex: 1; }
@media (max-width: 560px) {
  .tab .lbl { display: none; }
  .tab .ico { font-size: 1.25rem; }
  .tab.cta .lbl { display: inline; }
}
</style>
