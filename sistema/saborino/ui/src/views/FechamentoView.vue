<script setup>
import { ref, watch } from 'vue'
import api from '@/api/client'
import { useCompetenciaStore } from '@/stores/competencia'
import { brl } from '@/utils/format'

const comp = useCompetenciaStore()
const f = ref(null)

async function carregar() {
  if (!comp.atual) return
  const { data } = await api.get('/relatorios/fechamento/', { params: { competencia: comp.atual.id } })
  f.value = data
}
watch(() => comp.atual, carregar, { immediate: true })
const SOCIO = { NOS: 'Nós', S1: 'Sócio 1', S2: 'Sócio 2' }
</script>

<template>
  <div class="page" v-if="f">
    <div class="page-head"><h1>Fechamento de {{ f.competencia.rotulo }}</h1></div>
    <div class="grid cols">
      <div class="card">
        <div class="card-title">Resultado</div>
        <div class="lin"><span>Vendido</span><strong class="num">{{ brl(f.vendido) }}</strong></div>
        <div class="lin"><span>Custo (compras)</span><strong class="num">− {{ brl(f.custo_compras) }}</strong></div>
        <div class="lin total"><span>Resultado por competência</span><strong class="num">{{ brl(f.resultado_competencia) }}</strong></div>
        <div class="lin muted"><span>Resultado por caixa</span><span class="num">{{ brl(f.resultado_caixa) }}</span></div>
      </div>
      <div class="card">
        <div class="card-title">Deduções</div>
        <div class="lin"><span>Dízimo ({{ f.config.dizimo_percentual }}%)</span><strong class="num">− {{ brl(f.dizimo) }}</strong></div>
        <div class="lin"><span>Pró-labore</span><strong class="num">− {{ brl(f.prolabore) }}</strong></div>
        <div class="lin total"><span>Líquido após deduções</span><strong class="num">{{ brl(f.liquido_depois_deducoes) }}</strong></div>
        <p class="muted" style="font-size:.8rem">Ajuste os percentuais em Config.</p>
      </div>
      <div class="card">
        <div class="card-title">Divisão por sócio (destino da venda)</div>
        <div v-if="!f.split_por_socio.length" class="muted">Sem dados.</div>
        <div v-for="s in f.split_por_socio" :key="s.socio_destino" class="lin">
          <span>{{ SOCIO[s.socio_destino] || s.socio_destino }}</span><strong class="num">{{ brl(s.total) }}</strong>
        </div>
      </div>
    </div>
  </div>
</template>
<style scoped>
.cols { grid-template-columns: 1fr; }
@media (min-width: 820px) { .cols { grid-template-columns: repeat(3, 1fr); } }
.lin { display: flex; justify-content: space-between; padding: .4rem 0; border-bottom: 1px solid var(--hairline); }
.lin.total { border-top: 2px solid var(--hairline); border-bottom: none; margin-top: .3rem; padding-top: .6rem; font-size: 1.05rem; }
</style>
