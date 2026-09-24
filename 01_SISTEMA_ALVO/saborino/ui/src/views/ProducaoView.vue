<script setup>
import { ref, watch } from 'vue'
import api from '@/api/client'
import { useCompetenciaStore } from '@/stores/competencia'
import { num } from '@/utils/format'
import { useToast } from '@/composables/useToast'

const comp = useCompetenciaStore()
const { toast } = useToast()
const linhas = ref([])
const carregando = ref(false)

async function carregar() {
  if (!comp.atual) return
  carregando.value = true
  try {
    const [{ data: rel }, { data: prods }] = await Promise.all([
      api.get('/relatorios/por-produto/', { params: { competencia: comp.atual.id } }),
      api.get('/producoes/', { params: { competencia: comp.atual.id } }),
    ])
    const prodMap = new Map(prods.map((p) => [p.produto, p]))
    linhas.value = rel.map((r) => ({
      ...r,
      producao_id: prodMap.get(r.produto)?.id || null,
      quantidade_produzida: Number(prodMap.get(r.produto)?.quantidade_produzida ?? r.produzido),
    }))
  } finally {
    carregando.value = false
  }
}
async function salvarProducao(l) {
  const payload = { produto: l.produto, competencia: comp.atual.id, quantidade_produzida: l.quantidade_produzida || 0 }
  if (l.producao_id) await api.patch(`/producoes/${l.producao_id}/`, payload)
  else await api.post('/producoes/', payload)
  toast('Produção salva'); carregar()
}
watch(() => comp.atual, carregar, { immediate: true })
</script>

<template>
  <div class="page">
    <div class="page-head"><h1>Produção de {{ comp.atual?.rotulo }}</h1></div>
    <div class="card">
      <p class="muted" style="margin-top:0">Informe quanto produziu de cada item no mês. "Faltam vender" = produzido − vendido.</p>
      <div v-if="carregando" class="empty">Carregando…</div>
      <div class="table-wrap" v-else>
        <table class="data">
          <thead><tr><th>Produto</th><th class="num">Vendido</th><th class="num">Produzido</th><th class="num">Faltam vender</th><th></th></tr></thead>
          <tbody>
            <tr v-for="l in linhas" :key="l.produto">
              <td>{{ l.produto_nome }}</td>
              <td class="num">{{ num(l.vendido) }}</td>
              <td class="num"><input class="input mini" type="number" step="0.001" v-model="l.quantidade_produzida" /></td>
              <td class="num">{{ num(Number(l.quantidade_produzida) - Number(l.vendido)) }}</td>
              <td class="right"><button class="btn btn-sm" @click="salvarProducao(l)">Salvar</button></td>
            </tr>
          </tbody>
        </table>
        <div v-if="!linhas.length" class="empty">Sem produtos com movimento neste mês.</div>
      </div>
    </div>
  </div>
</template>
<style scoped>.mini { min-height: 34px; width: 7rem; text-align: right; margin-left: auto; }</style>
