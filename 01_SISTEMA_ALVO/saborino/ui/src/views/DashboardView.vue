<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import { useCompetenciaStore } from '@/stores/competencia'
import { brl, num, pct } from '@/utils/format'

const comp = useCompetenciaStore()
const router = useRouter()
const d = ref(null)
const carregando = ref(false)

async function carregar() {
  if (!comp.atual) return
  carregando.value = true
  try {
    const { data } = await api.get('/relatorios/dashboard/', { params: { competencia: comp.atual.id } })
    d.value = data
  } finally {
    carregando.value = false
  }
}
watch(() => comp.atual, carregar, { immediate: true })
</script>

<template>
  <div class="page">
    <div class="page-head">
      <h1>Painel de {{ comp.atual?.rotulo || '—' }}</h1>
      <div class="spacer"></div>
      <button class="btn btn-primary btn-sm" @click="router.push('/venda')">➕ Nova venda</button>
    </div>

    <div v-if="carregando && !d" class="empty">Carregando…</div>

    <template v-else-if="d">
      <div class="tiles">
        <div class="tile"><div class="l">Vendido</div><div class="v">{{ brl(d.vendido) }}</div>
          <div class="s" v-if="d.tem_mes_anterior && d.delta_vendido_pct !== null"
               :class="d.delta_vendido_pct >= 0 ? 'up' : 'down'">{{ pct(d.delta_vendido_pct) }} vs mês anterior</div>
        </div>
        <div class="tile clic" @click="router.push('/a-receber')">
          <div class="l">A receber</div><div class="v warn">{{ brl(d.a_receber) }}</div>
          <div class="s">recebido {{ brl(d.recebido) }}</div>
        </div>
        <div class="tile"><div class="l">Resultado (competência)</div>
          <div class="v" :class="Number(d.resultado_competencia) >= 0 ? 'good' : 'crit'">{{ brl(d.resultado_competencia) }}</div>
          <div class="s">caixa {{ brl(d.resultado_caixa) }}</div>
        </div>
        <div class="tile"><div class="l">Potes vendidos</div><div class="v">{{ num(d.potes_vendidos) }}</div>
          <div class="s">faltam vender {{ num(d.faltam_vender) }}</div>
        </div>
        <div class="tile"><div class="l">Ticket médio</div><div class="v">{{ brl(d.ticket_medio) }}</div>
          <div class="s">{{ d.num_vendas }} vendas</div>
        </div>
        <div class="tile"><div class="l">Custo (compras)</div><div class="v">{{ brl(d.custo_compras) }}</div>
          <div class="s">dízimo estim. {{ brl(d.dizimo_estimado) }}</div>
        </div>
      </div>

      <div class="cols">
        <div class="card">
          <div class="card-title">Ranking de produtos</div>
          <div v-if="!d.ranking_produtos.length" class="muted">Sem vendas ainda.</div>
          <table v-else class="data">
            <thead><tr><th>Produto</th><th class="num">Qtd</th><th class="num">Valor</th></tr></thead>
            <tbody>
              <tr v-for="r in d.ranking_produtos" :key="r.produto__nome">
                <td>{{ r.produto__nome }}</td>
                <td class="num">{{ num(r.qtd) }}</td>
                <td class="num">{{ brl(r.valor) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="card">
          <div class="card-title">Entradas por forma</div>
          <div v-if="!d.entradas_por_forma.length" class="muted">Sem recebimentos.</div>
          <table v-else class="data">
            <tbody>
              <tr v-for="e in d.entradas_por_forma" :key="e.forma_pagamento">
                <td>{{ e.forma_pagamento || '—' }}</td>
                <td class="num">{{ brl(e.total) }}</td>
              </tr>
            </tbody>
          </table>
          <div class="card-title" style="margin-top:1rem">Vendas por procedência</div>
          <table class="data">
            <tbody>
              <tr v-for="c in d.vendas_por_canal" :key="c.canal__nome">
                <td>{{ c.canal__nome || 'Sem canal' }}</td>
                <td class="num">{{ brl(c.total) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="card">
          <div class="card-title">Últimas vendas</div>
          <div v-if="!d.feed.length" class="muted">Nada por aqui.</div>
          <table v-else class="data">
            <tbody>
              <tr v-for="f in d.feed" :key="f.id">
                <td>{{ f.cliente__nome }}</td>
                <td class="muted">{{ f.data_venda }}</td>
                <td class="num">{{ brl(f.valor_total) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(9.5rem, 1fr)); gap: .8rem; margin-bottom: 1.2rem; }
.tile { background: var(--surface); border: 1px solid var(--hairline); border-radius: var(--radius); box-shadow: var(--shadow); padding: .9rem 1rem; }
.tile.clic { cursor: pointer; }
.tile .l { font-size: .78rem; color: var(--muted); }
.tile .v { font-size: 1.5rem; font-weight: 800; font-variant-numeric: tabular-nums; margin-top: .1rem; }
.tile .v.warn { color: var(--warn); } .tile .v.good { color: var(--good); } .tile .v.crit { color: var(--crit); }
.tile .s { font-size: .76rem; color: var(--muted); margin-top: .15rem; }
.tile .s.up { color: var(--good); } .tile .s.down { color: var(--crit); }
.cols { display: grid; gap: 1rem; grid-template-columns: 1fr; }
@media (min-width: 820px) { .cols { grid-template-columns: 1fr 1fr; } }
</style>
