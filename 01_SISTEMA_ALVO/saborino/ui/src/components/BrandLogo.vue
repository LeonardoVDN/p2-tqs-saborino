<script setup>
defineProps({ compact: Boolean })
</script>

<template>
  <img class="brand-logo" :class="{ compact }" src="/saborino-logo.png"
       alt="Doceria Saborino" width="1136" height="1132" decoding="async" />
</template>

<style scoped>
.brand-logo {
  display: block;
  width: min(12rem, 100%);
  height: auto;
  object-fit: contain;
  margin: 0 auto 1rem;
  border-radius: .75rem;
}
.brand-logo.compact { width: 5rem; margin: 0; border-radius: .5rem; }
</style>
