<script setup>
import { ref, computed, watch } from 'vue'
import api from '@/api/client'
import { useCompetenciaStore } from '@/stores/competencia'
import { brl } from '@/utils/format'
import { useToast } from '@/composables/useToast'

const comp = useCompetenciaStore()
const { toast } = useToast()
const itens = ref([])
const carregando = ref(false)
const FORMAS = ['PIX', 'DINHEIRO', 'CARTAO', 'OUTRO']

// pagamento consolidado
const pagCliente = ref(null)
const pagValor = ref('')
const pagForma = ref('PIX')

const totalAberto = computed(() => itens.value.reduce((s, r) => s + Number(r.a_receber), 0))
const clientesComSaldo = computed(() => {
  const map = new Map()
  for (const r of itens.value) {
    const cur = map.get(r.cliente) || { id: r.cliente, nome: r.cliente_nome, total: 0 }
    cur.total += Number(r.a_receber)
    map.set(r.cliente, cur)
  }
  return [...map.values()]
})

async function carregar() {
  if (!comp.atual) return
  carregando.value = true
  try {
    const { data } = await api.get('/recebiveis/em_aberto/', { params: { competencia: comp.atual.id } })
    itens.value = data
  } finally {
    carregando.value = false
  }
}
watch(() => comp.atual, carregar, { immediate: true })

async function quitar(r, forma) {
  await api.post(`/vendas/${r.venda}/quitar/`, { forma_pagamento: forma })
  toast('Recebido!')
  carregar()
}

async function registrarPagamento() {
  if (!pagCliente.value || !pagValor.value) return
  await api.post('/pagamentos/', {
    cliente: pagCliente.value, valor: pagValor.value, forma_pagamento: pagForma.value,
  })
  toast('Pagamento registrado')
  pagCliente.value = null; pagValor.value = ''
  carregar()
}

function whatsapp(r) {
  const texto = `Oi ${r.cliente_nome}! Passando pra lembrar do pedido da Saborino: ${brl(r.a_receber)} em aberto. Pode ser no Pix quando puder 💛`
  window.open(`https://wa.me/?text=${encodeURIComponent(texto)}`, '_blank')
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <h1>A receber</h1><div class="spacer"></div>
      <span class="chip chip-static">Total em aberto: <strong>{{ brl(totalAberto) }}</strong></span>
    </div>

    <div class="card">
      <div class="card-title">Registrar pagamento do cliente (parcial ou de várias vendas)</div>
      <div class="row">
        <select class="select" v-model="pagCliente" style="max-width:16rem">
          <option :value="null">Escolha o cliente…</option>
          <option v-for="c in clientesComSaldo" :key="c.id" :value="c.id">{{ c.nome }} — deve {{ brl(c.total) }}</option>
        </select>
        <input class="input" style="max-width:9rem" type="number" step="0.01" placeholder="Valor" v-model="pagValor" />
        <button v-for="f in FORMAS" :key="f" class="chip" :class="{ on: pagForma === f }" @click="pagForma = f">{{ f }}</button>
        <button class="btn btn-good" @click="registrarPagamento" :disabled="!pagCliente || !pagValor">Registrar</button>
      </div>
      <p class="muted" style="font-size:.8rem;margin:.5rem 0 0">O valor é alocado automaticamente do pedido mais antigo ao mais novo.</p>
    </div>

    <div class="card" style="margin-top:1rem">
      <div v-if="carregando" class="empty">Carregando…</div>
      <div v-else-if="!itens.length" class="empty">Ninguém devendo neste mês 🎉</div>
      <div class="table-wrap" v-else>
        <table class="data">
          <thead><tr><th>Cliente</th><th>Venda</th><th class="num">A receber</th><th>Status</th><th></th></tr></thead>
          <tbody>
            <tr v-for="r in itens" :key="r.id">
              <td>{{ r.cliente_nome }}</td>
              <td class="muted">#{{ r.venda }} · {{ r.data_venda }}</td>
              <td class="num">{{ brl(r.a_receber) }}</td>
              <td><span class="badge" :class="'badge-' + r.status.toLowerCase()">{{ r.status }}</span></td>
              <td class="right acts">
                <button class="btn btn-sm btn-good" @click="quitar(r, 'PIX')">✓ Pix</button>
                <button class="btn btn-sm" @click="quitar(r, 'DINHEIRO')">✓ Dinheiro</button>
                <button class="btn btn-sm btn-ghost" @click="whatsapp(r)">💬</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.acts { display: flex; gap: .3rem; justify-content: flex-end; flex-wrap: wrap; }
</style>
