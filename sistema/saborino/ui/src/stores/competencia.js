import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api/client'

// Competência ativa = filtro global SÓ-LEITURA de relatórios/histórico.
// Nunca é o alvo de gravação: lançamentos derivam a competência da própria data.
export const useCompetenciaStore = defineStore('competencia', () => {
  const atual = ref(null)
  const lista = ref([])
  const carregando = ref(false)

  async function inicializar() {
    carregando.value = true
    try {
      const [{ data: hoje }, { data: todas }] = await Promise.all([
        api.get('/competencias/atual/'),
        api.get('/competencias/'),
      ])
      lista.value = todas
      atual.value = todas.find((c) => c.id === hoje.id) || hoje
      if (!todas.some((c) => c.id === hoje.id)) lista.value = [hoje, ...todas]
    } finally {
      carregando.value = false
    }
  }

  function selecionar(id) {
    const c = lista.value.find((x) => x.id === Number(id))
    if (c) atual.value = c
  }

  return { atual, lista, carregando, inicializar, selecionar }
})
