<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api/client'
import { brl } from '@/utils/format'
import { useToast } from '@/composables/useToast'

const { toast } = useToast()
const produtos = ref([])
const form = ref(null)
const CATEGORIAS = [
  ['BOLO_POTE', 'Bolo de pote'], ['MOUSSE', 'Mousse'], ['PUDIM', 'Pudim'],
  ['TORTA', 'Torta'], ['BROWNIE', 'Brownie'], ['OVO_PASCOA', 'Ovo de Páscoa'],
  ['ENERGETICO', 'Energético'], ['OUTRO', 'Outro'],
]

function novo() {
  form.value = { nome: '', categoria: 'BOLO_POTE', unidade: 'POTE', preco_venda: '', custo_estimado_unitario: '', sazonal: false, ativo: true }
}
function editar(p) { form.value = { ...p } }

async function carregar() {
  const { data } = await api.get('/produtos/')
  produtos.value = data
}
async function salvar() {
  const f = form.value
  const payload = { ...f, preco_venda: f.preco_venda || 0, custo_estimado_unitario: f.custo_estimado_unitario || 0 }
  if (f.id) await api.put(`/produtos/${f.id}/`, payload)
  else await api.post('/produtos/', payload)
  toast('Produto salvo'); form.value = null; carregar()
}
onMounted(carregar)
</script>

<template>
  <div class="page">
    <div class="page-head"><h1>Produtos</h1><div class="spacer"></div>
      <button class="btn btn-primary" @click="novo">➕ Novo produto</button></div>

    <div v-if="form" class="card" style="margin-bottom:1rem">
      <div class="card-title">{{ form.id ? 'Editar' : 'Novo' }} produto</div>
      <div class="grid2">
        <div class="field"><label>Nome</label><input class="input" v-model="form.nome" /></div>
        <div class="field"><label>Categoria</label>
          <select class="select" v-model="form.categoria">
            <option v-for="[v,l] in CATEGORIAS" :key="v" :value="v">{{ l }}</option>
          </select></div>
        <div class="field"><label>Preço de venda</label><input class="input" type="number" step="0.01" v-model="form.preco_venda" /></div>
        <div class="field"><label>Custo estimado (un)</label><input class="input" type="number" step="0.01" v-model="form.custo_estimado_unitario" /></div>
      </div>
      <div class="row">
        <label class="chk"><input type="checkbox" v-model="form.sazonal" /> Sazonal</label>
        <label class="chk"><input type="checkbox" v-model="form.ativo" /> Ativo</label>
        <div class="spacer"></div>
        <button class="btn btn-ghost" @click="form = null">Cancelar</button>
        <button class="btn btn-primary" @click="salvar" :disabled="!form.nome">Salvar</button>
      </div>
    </div>

    <div class="card">
      <div class="table-wrap">
        <table class="data">
          <thead><tr><th>Produto</th><th>Categoria</th><th class="num">Preço</th><th class="num">Custo est.</th><th></th><th></th></tr></thead>
          <tbody>
            <tr v-for="p in produtos" :key="p.id">
              <td>{{ p.nome }} <span v-if="!p.ativo" class="muted">(inativo)</span></td>
              <td class="muted">{{ p.categoria_display }}</td>
              <td class="num">{{ brl(p.preco_venda) }}</td>
              <td class="num muted">{{ brl(p.custo_estimado_unitario) }}</td>
              <td><span v-if="p.sazonal" class="chip chip-static">sazonal</span></td>
              <td class="right"><button class="btn btn-sm" @click="editar(p)">Editar</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
<style scoped>
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0 1rem; }
.chk { display: flex; align-items: center; gap: .4rem; font-size: .9rem; }
@media (max-width: 560px) { .grid2 { grid-template-columns: 1fr; } }
</style>
