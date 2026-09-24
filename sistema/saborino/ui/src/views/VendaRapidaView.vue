<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api/client'
import { brl, num } from '@/utils/format'
import { useToast } from '@/composables/useToast'

const { toast } = useToast()

const produtos = ref([])
const carrinho = ref([]) // {produto, nome, preco, quantidade, subtotal}
const buscaCliente = ref('')
const clientes = ref([])
const clienteSel = ref(null)
const mostrarBusca = ref(false)
const pagarAgora = ref(true)
const forma = ref('PIX')
const salvando = ref(false)

const FORMAS = ['PIX', 'DINHEIRO', 'CARTAO', 'OUTRO']

const total = computed(() => carrinho.value.reduce((s, i) => s + Number(i.subtotal || 0), 0))
const podeSalvar = computed(() => clienteSel.value && carrinho.value.length > 0 && !salvando.value)

async function carregarProdutos() {
  const { data } = await api.get('/produtos/', { params: { ativo: 'true' } })
  produtos.value = data
}

let buscaTimer = null
function onBuscaCliente() {
  mostrarBusca.value = true
  clienteSel.value = null
  clearTimeout(buscaTimer)
  buscaTimer = setTimeout(async () => {
    const q = buscaCliente.value.trim()
    if (!q) { clientes.value = []; return }
    const { data } = await api.get('/clientes/', { params: { q, ativo: 'true' } })
    clientes.value = data.slice(0, 8)
  }, 220)
}

function escolherCliente(c) {
  clienteSel.value = c
  buscaCliente.value = c.nome
  mostrarBusca.value = false
}

async function criarCliente() {
  const nome = buscaCliente.value.trim()
  if (!nome) return
  const { data } = await api.post('/clientes/', { nome })
  escolherCliente(data)
  toast('Cliente criado')
}

function addProduto(p) {
  const existe = carrinho.value.find((i) => i.produto === p.id)
  if (existe) {
    existe.quantidade = Number(existe.quantidade) + 1
    existe.subtotal = (existe.quantidade * Number(existe.preco)).toFixed(2)
  } else {
    carrinho.value.push({
      produto: p.id, nome: p.nome, preco: Number(p.preco_venda),
      quantidade: 1, subtotal: Number(p.preco_venda).toFixed(2),
    })
  }
}
function ajustarQtd(item, delta) {
  item.quantidade = Math.max(1, Number(item.quantidade) + delta)
  item.subtotal = (item.quantidade * Number(item.preco)).toFixed(2)
}
function removerItem(item) {
  carrinho.value = carrinho.value.filter((i) => i.produto !== item.produto)
}
function onSubtotalManual(item) {
  // Permite ajuste manual (brinde/desconto) sem recalcular pela quantidade.
  item.subtotal = Number(item.subtotal || 0).toFixed(2)
}

async function repetirUltimo() {
  if (!clienteSel.value) { toast('Escolha um cliente primeiro'); return }
  const { data } = await api.get(`/vendas/repetir-ultimo/${clienteSel.value.id}/`)
  if (!data.itens?.length) { toast('Sem pedido anterior'); return }
  carrinho.value = data.itens.map((i) => ({
    produto: i.produto, nome: i.produto_nome, preco: Number(i.preco_unitario),
    quantidade: Number(i.quantidade),
    subtotal: (Number(i.quantidade) * Number(i.preco_unitario)).toFixed(2),
  }))
  toast('Último pedido carregado')
}

async function salvar(novaEmSeguida) {
  if (!podeSalvar.value) return
  salvando.value = true
  try {
    await api.post('/vendas/', {
      cliente: clienteSel.value.id,
      itens_input: carrinho.value.map((i) => ({
        produto: i.produto, quantidade: i.quantidade, subtotal: i.subtotal,
      })),
      pagar_agora: pagarAgora.value,
      forma_pagamento: forma.value,
    })
    toast(pagarAgora.value ? 'Venda registrada e paga' : 'Venda registrada (fiado)')
    carrinho.value = []
    if (novaEmSeguida) {
      // mantém o cliente para pedidos em sequência? Limpa para o próximo.
      clienteSel.value = null
      buscaCliente.value = ''
    }
  } catch (e) {
    toast('Erro ao salvar venda')
  } finally {
    salvando.value = false
  }
}

onMounted(carregarProdutos)
</script>

<template>
  <div class="page">
    <div class="page-head"><h1>Nova venda</h1></div>

    <div class="card">
      <div class="field" style="position:relative">
        <label>Cliente</label>
        <input class="input" v-model="buscaCliente" @input="onBuscaCliente"
               placeholder="Buscar ou digitar novo…" />
        <div v-if="mostrarBusca && buscaCliente" class="dropdown">
          <button v-for="c in clientes" :key="c.id" class="opt" @click="escolherCliente(c)">
            {{ c.nome }} <span class="muted" v-if="c.canal_nome">· {{ c.canal_nome }}</span>
          </button>
          <button class="opt novo" @click="criarCliente">➕ Criar cliente "{{ buscaCliente }}"</button>
        </div>
      </div>
      <div v-if="clienteSel" class="row">
        <span class="chip on chip-static">✓ {{ clienteSel.nome }}</span>
        <button class="btn btn-sm btn-ghost" @click="repetirUltimo">🔁 Repetir último</button>
      </div>
    </div>

    <div class="card" style="margin-top:1rem">
      <div class="card-title">Produtos</div>
      <div class="prod-grid">
        <button v-for="p in produtos" :key="p.id" class="prod" @click="addProduto(p)">
          <span class="pn">{{ p.nome }}</span>
          <span class="pp">{{ brl(p.preco_venda) }}</span>
        </button>
      </div>
      <div v-if="!produtos.length" class="muted">Nenhum produto ativo. Cadastre em Produtos.</div>
    </div>

    <div class="card cart" v-if="carrinho.length" style="margin-top:1rem">
      <div class="card-title">Pedido</div>
      <div v-for="item in carrinho" :key="item.produto" class="cart-row">
        <div class="ci-nome">{{ item.nome }}</div>
        <div class="qty">
          <button class="btn btn-sm" @click="ajustarQtd(item, -1)">−</button>
          <span class="num">{{ num(item.quantidade) }}</span>
          <button class="btn btn-sm" @click="ajustarQtd(item, 1)">+</button>
        </div>
        <input class="input sub" type="number" step="0.01" v-model="item.subtotal" @change="onSubtotalManual(item)" />
        <button class="btn btn-sm btn-ghost" @click="removerItem(item)">✕</button>
      </div>
      <div class="total-row"><span>Total</span><strong class="num">{{ brl(total) }}</strong></div>

      <div class="pay">
        <div class="row">
          <span class="muted">Pagamento:</span>
          <button class="chip" :class="{ on: pagarAgora }" @click="pagarAgora = true">Pago agora</button>
          <button class="chip" :class="{ on: !pagarAgora }" @click="pagarAgora = false">Fiado</button>
        </div>
        <div class="row" v-if="pagarAgora" style="margin-top:.5rem">
          <button v-for="f in FORMAS" :key="f" class="chip" :class="{ on: forma === f }" @click="forma = f">{{ f }}</button>
        </div>
      </div>

      <div class="row" style="margin-top:1rem">
        <button class="btn btn-primary" :disabled="!podeSalvar" @click="salvar(false)">Salvar venda</button>
        <button class="btn" :disabled="!podeSalvar" @click="salvar(true)">Salvar + nova</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dropdown { position: absolute; top: 100%; left: 0; right: 0; z-index: 30; margin-top: .2rem;
  background: var(--surface); border: 1px solid var(--hairline); border-radius: 10px; box-shadow: var(--shadow); overflow: hidden; }
.opt { display: block; width: 100%; text-align: left; padding: .6rem .8rem; background: none; border: none; border-bottom: 1px solid var(--hairline); cursor: pointer; }
.opt:hover { background: var(--surface-2); }
.opt.novo { color: var(--accent-ink); font-weight: 600; }
.prod-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(8rem, 1fr)); gap: .6rem; }
.prod { display: flex; flex-direction: column; gap: .2rem; padding: .8rem; border: 1px solid var(--hairline); border-radius: 10px; background: var(--surface); cursor: pointer; text-align: left; }
.prod:hover { border-color: var(--accent); background: var(--accent-soft); }
.prod .pn { font-weight: 600; font-size: .9rem; }
.prod .pp { color: var(--accent-ink); font-weight: 700; }
.cart-row { display: grid; grid-template-columns: 1fr auto 6rem auto; gap: .5rem; align-items: center; padding: .5rem 0; border-bottom: 1px solid var(--hairline); }
.ci-nome { font-weight: 600; }
.qty { display: flex; align-items: center; gap: .5rem; }
.sub { min-height: 38px; text-align: right; }
.total-row { display: flex; justify-content: space-between; padding: .8rem 0 .2rem; font-size: 1.1rem; }
.pay { margin-top: .6rem; }
@media (max-width: 520px) {
  .cart-row { grid-template-columns: 1fr auto; grid-auto-rows: auto; }
  .sub { grid-column: 1 / 2; }
}
</style>
