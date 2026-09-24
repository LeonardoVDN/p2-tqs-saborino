<script setup>
import { ref, computed, watch } from 'vue'
import api from '@/api/client'
import { useCompetenciaStore } from '@/stores/competencia'
import { brl, num } from '@/utils/format'

const comp = useCompetenciaStore()
const vendas = ref([])
const carregando = ref(false)
const busca = ref('')

const filtradas = computed(() => {
  const q = busca.value.trim().toLowerCase()
  if (!q) return vendas.value
  return vendas.value.filter((v) => v.cliente_nome.toLowerCase().includes(q))
})
const total = computed(() => filtradas.value.reduce((s, v) => s + Number(v.valor_total), 0))

async function carregar() {
  if (!comp.atual) return
  carregando.value = true
  try {
    const { data } = await api.get('/vendas/', { params: { competencia: comp.atual.id } })
    vendas.value = data
  } finally {
    carregando.value = false
  }
}
watch(() => comp.atual, carregar, { immediate: true })
</script>

<template>
  <div class="page">
    <div class="page-head"><h1>Vendas de {{ comp.atual?.rotulo }}</h1></div>
    <div class="card">
      <input class="input" v-model="busca" placeholder="Buscar cliente…" style="margin-bottom:.8rem" />
      <div v-if="carregando" class="empty">Carregando…</div>
      <div v-else-if="!filtradas.length" class="empty">Nenhuma venda.</div>
      <div class="table-wrap" v-else>
        <table class="data">
          <thead><tr><th>Cliente</th><th>Data</th><th>Itens</th><th class="num">Total</th><th>Recebível</th></tr></thead>
          <tbody>
            <tr v-for="v in filtradas" :key="v.id">
              <td>{{ v.cliente_nome }}</td>
              <td class="muted">{{ v.data_venda }}</td>
              <td class="muted">{{ v.itens.map(i => num(i.quantidade) + 'x ' + i.produto_nome).join(', ') }}</td>
              <td class="num">{{ brl(v.valor_total) }}</td>
              <td><span v-if="v.recebivel" class="badge" :class="'badge-' + v.recebivel.status.toLowerCase()">{{ v.recebivel.status }}</span></td>
            </tr>
          </tbody>
          <tfoot><tr><th colspan="3">Total ({{ filtradas.length }})</th><th class="num">{{ brl(total) }}</th><th></th></tr></tfoot>
        </table>
      </div>
    </div>
  </div>
</template>
