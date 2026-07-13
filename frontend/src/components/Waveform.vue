<script setup lang="ts">
defineProps<{ progress?: number }>()
</script>
<template><div class="waveform" :style="{ '--wave-progress': `${progress ?? 0}%` }" aria-label="音频波形"><i v-for="n in 52" :key="n" :style="{ height: `${8 + ((n * 17) % 24)}px` }" /></div></template>
