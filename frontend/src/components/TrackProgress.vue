<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ currentTime: number; duration: number; label: string; testId?: string }>()
const emit = defineEmits<{ seek: [seconds: number] }>()
const safeDuration = computed(() => Number.isFinite(props.duration) && props.duration > 0 ? props.duration : 0)
const safeTime = computed(() => Math.min(safeDuration.value, Math.max(0, props.currentTime || 0)))
const percentage = computed(() => safeDuration.value ? safeTime.value / safeDuration.value * 100 : 0)
function seek(event: Event) { emit('seek', Number((event.target as HTMLInputElement).value)) }
</script>

<template><input class="track-progress" type="range" role="slider" min="0" :max="safeDuration" step="0.1" :value="safeTime" :aria-label="label" :data-testid="testId" :disabled="safeDuration === 0" :style="{ '--track-progress': `${percentage}%` }" @input="seek" /></template>
