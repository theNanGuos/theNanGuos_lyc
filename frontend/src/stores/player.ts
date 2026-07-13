import { defineStore } from 'pinia'

export interface Track { requestId: string; audioId: string; title: string; subtitle: string; audioUrl: string; coverUrl: string; downloadUrl?: string }
export const usePlayerStore = defineStore('player', {
  state: () => ({ current: null as Track | null, playing: false, currentTime: 0, duration: 0, volume: 0.75 }),
  actions: {
    select(track: Track) {
      if (this.current?.audioId === track.audioId) { this.playing = !this.playing; return }
      this.current = track; this.currentTime = 0; this.duration = 0; this.playing = true
    },
    toggle() { if (this.current) this.playing = !this.playing },
  },
})
