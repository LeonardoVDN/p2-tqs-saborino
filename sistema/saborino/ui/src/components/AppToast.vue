<script setup>
import { useToast } from '@/composables/useToast'
const { state } = useToast()
</script>
<template>
  <Transition name="fade">
    <div v-if="state.visible" class="toast">{{ state.msg }}</div>
  </Transition>
</template>
<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity .2s, transform .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: translate(-50%, 8px); }
</style>
