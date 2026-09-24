<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api/client'
import { useToast } from '@/composables/useToast'

const { toast } = useToast()
const clientes = ref([])
const canais = ref([])
const form = ref(null)
const busca = ref('')

function novo() { form.value = { nome: '', canal: null, contato: '', forma_pagamento_preferida: '', ativo: true } }
function editar(c) { form.value = { ...c } }

async function carregar() {
  const [{ data: cs }, { data: cn }] = await Promise.all([
    api.get('/clientes/', { params: busca.value ? { q: busca.value } : {} }),
    api.get('/canais/', { params: { ativo: 'true' } }),
  ])
  clientes.value = cs; canais.value = cn
}
async function salvar() {
  const f = form.value
  if (f.id) await api.put(`/clientes/${f.id}/`, f)
  else await api.post('/clientes/', f)
  toast('Cliente salvo'); form.value = null; carregar()
}
onMounted(carregar)
</script>

<template>
  <div class="page">
    <div class="page-head"><h1>Clientes</h1><div class="spacer"></div>
      <button class="btn btn-primary" @click="novo">➕ Novo cliente</button></div>

    <div v-if="form" class="card" style="margin-bottom:1rem">
      <div class="card-title">{{ form.id ? 'Editar' : 'Novo' }} cliente</div>
      <div class="field"><label>Nome</label><input class="input" v-model="form.nome" /></div>
      <div class="row">
        <div class="field" style="flex:1;min-width:10rem"><label>Canal / procedência</label>
          <select class="select" v-model="form.canal">
            <option :value="null">—</option>
            <option v-for="c in canais" :key="c.id" :value="c.id">{{ c.nome }}</option>
          </select></div>
        <div class="field" style="flex:1;min-width:10rem"><label>Contato (WhatsApp)</label>
          <input class="input" v-model="form.contato" /></div>
      </div>
      <div class="row">
        <div class="spacer"></div>
        <button class="btn btn-ghost" @click="form = null">Cancelar</button>
        <button class="btn btn-primary" @click="salvar" :disabled="!form.nome">Salvar</button>
      </div>
    </div>

    <div class="card">
      <input class="input" v-model="busca" @input="carregar" placeholder="Buscar…" style="margin-bottom:.8rem" />
      <div class="table-wrap">
        <table class="data">
          <thead><tr><th>Nome</th><th>Canal</th><th>Contato</th><th></th></tr></thead>
          <tbody>
            <tr v-for="c in clientes" :key="c.id">
              <td>{{ c.nome }}</td><td class="muted">{{ c.canal_nome || '—' }}</td>
              <td class="muted">{{ c.contato || '—' }}</td>
              <td class="right"><button class="btn btn-sm" @click="editar(c)">Editar</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
