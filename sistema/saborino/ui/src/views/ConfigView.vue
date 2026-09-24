<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api/client'
import { useToast } from '@/composables/useToast'

const { toast } = useToast()
const c = ref(null)

async function carregar() { const { data } = await api.get('/config-financeira/'); c.value = data }
async function salvar() {
  const { data } = await api.put('/config-financeira/', c.value)
  c.value = data; toast('Configuração salva')
}
onMounted(carregar)
</script>

<template>
  <div class="page" v-if="c">
    <div class="page-head"><h1>Configuração financeira</h1></div>
    <div class="card" style="max-width:34rem">
      <div class="field"><label>Dízimo — percentual sobre o lucro do mês (%)</label>
        <input class="input" type="number" step="0.01" v-model="c.dizimo_percentual" /></div>
      <label class="chk"><input type="checkbox" v-model="c.dizimo_ativo" /> Calcular dízimo no fechamento</label>
      <hr style="border:none;border-top:1px solid var(--hairline);margin:1rem 0" />
      <div class="field"><label>Pró-labore — percentual sobre o lucro (%)</label>
        <input class="input" type="number" step="0.01" v-model="c.prolabore_percentual" /></div>
      <div class="field"><label>Pró-labore — valor fixo (usado se preenchido)</label>
        <input class="input" type="number" step="0.01" v-model="c.prolabore_valor_fixo" /></div>
      <div class="row"><div class="spacer"></div><button class="btn btn-primary" @click="salvar">Salvar</button></div>
    </div>
  </div>
</template>
<style scoped>.chk { display: flex; align-items: center; gap: .4rem; font-size: .92rem; }</style>
