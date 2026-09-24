<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import api from '@/api/client'
import { useCompetenciaStore } from '@/stores/competencia'
import { brl } from '@/utils/format'
import { useToast } from '@/composables/useToast'

const comp = useCompetenciaStore()
const { toast } = useToast()
const compras = ref([])
const contas = ref([])
const produtos = ref([])
const form = ref(null)
const total = computed(() => compras.value.reduce((s, c) => s + Number(c.valor_total), 0))

function novo() {
  form.value = { data: new Date().toISOString().slice(0, 10), descricao: '', quantidade: 1, preco_unitario: '', valor_total: '', conta_origem: null, produto_rateio: null, situacao: 'PAGA' }
}
async function carregar() {
  if (!comp.atual) return
  const { data } = await api.get('/compras/', { params: { competencia: comp.atual.id } })
  compras.value = data
}
async function carregarAux() {
  const [{ data: ct }, { data: pr }] = await Promise.all([
    api.get('/contas/', { params: { ativo: 'true' } }),
    api.get('/produtos/', { params: { ativo: 'true' } }),
  ])
  contas.value = ct; produtos.value = pr
}
async function salvar() {
  const f = { ...form.value }
  if (!f.valor_total) f.valor_total = (Number(f.quantidade) * Number(f.preco_unitario || 0)).toFixed(2)
  await api.post('/compras/', f)
  toast('Compra registrada'); form.value = null; carregar()
}
watch(() => comp.atual, carregar, { immediate: true })
onMounted(carregarAux)
</script>

<template>
  <div class="page">
    <div class="page-head"><h1>Compras de {{ comp.atual?.rotulo }}</h1><div class="spacer"></div>
      <span class="chip chip-static">Total: <strong>{{ brl(total) }}</strong></span>
      <button class="btn btn-primary" @click="novo">➕ Nova compra</button></div>

    <div v-if="form" class="card" style="margin-bottom:1rem">
      <div class="card-title">Nova compra</div>
      <div class="row">
        <div class="field" style="flex:2;min-width:12rem"><label>Item</label><input class="input" v-model="form.descricao" /></div>
        <div class="field" style="width:6rem"><label>Qtd</label><input class="input" type="number" step="0.001" v-model="form.quantidade" /></div>
        <div class="field" style="width:8rem"><label>Preço un.</label><input class="input" type="number" step="0.01" v-model="form.preco_unitario" /></div>
        <div class="field" style="width:8rem"><label>Total (opc.)</label><input class="input" type="number" step="0.01" v-model="form.valor_total" placeholder="auto" /></div>
      </div>
      <div class="row">
        <div class="field" style="flex:1;min-width:9rem"><label>Conta</label>
          <select class="select" v-model="form.conta_origem"><option :value="null">—</option>
            <option v-for="c in contas" :key="c.id" :value="c.id">{{ c.nome }}</option></select></div>
        <div class="field" style="flex:1;min-width:9rem"><label>Rateio p/ produto</label>
          <select class="select" v-model="form.produto_rateio"><option :value="null">Geral</option>
            <option v-for="p in produtos" :key="p.id" :value="p.id">{{ p.nome }}</option></select></div>
        <div class="field" style="width:8rem"><label>Situação</label>
          <select class="select" v-model="form.situacao"><option value="PAGA">Paga</option><option value="A_PAGAR">A pagar</option></select></div>
      </div>
      <div class="row"><div class="spacer"></div>
        <button class="btn btn-ghost" @click="form = null">Cancelar</button>
        <button class="btn btn-primary" @click="salvar" :disabled="!form.descricao">Salvar</button></div>
    </div>

    <div class="card">
      <div class="table-wrap">
        <table class="data">
          <thead><tr><th>Item</th><th>Data</th><th>Conta</th><th>Rateio</th><th class="num">Valor</th></tr></thead>
          <tbody>
            <tr v-for="c in compras" :key="c.id">
              <td>{{ c.descricao }}</td><td class="muted">{{ c.data }}</td>
              <td class="muted">{{ c.conta_origem_nome || '—' }}</td>
              <td class="muted">{{ c.produto_rateio_nome }}</td>
              <td class="num">{{ brl(c.valor_total) }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="!compras.length" class="empty">Nenhuma compra.</div>
      </div>
    </div>
  </div>
</template>
