<script setup lang="ts">
import { Cog6ToothIcon, HomeIcon, MusicalNoteIcon } from '@heroicons/vue/24/outline'
</script>

<template>
  <aside class="sidebar">
    <RouterLink to="/" class="brand" aria-label="南郭先生们首页"><MusicalNoteIcon/><strong>南郭先生们</strong></RouterLink>
    <nav>
      <RouterLink to="/create"><HomeIcon />创作</RouterLink>
      <RouterLink to="/works"><MusicalNoteIcon />作品</RouterLink>
      <RouterLink to="/preferences"><Cog6ToothIcon />偏好设置</RouterLink>
    </nav>
  </aside>
</template>
