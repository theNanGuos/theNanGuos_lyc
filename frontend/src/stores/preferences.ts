import { defineStore } from 'pinia'
import { api, type UserDefaults } from '../api/client'

export const systemDefaults = (): UserDefaults => ({ language: 'zh', instrumental: false, vocal_gender: 'f', suno_model: 'V5' })
function mergeDefinedDefaults(defaults: Partial<UserDefaults> | null | undefined): UserDefaults {
  const merged = systemDefaults()
  if (!defaults) return merged
  for (const key of Object.keys(merged) as (keyof UserDefaults)[]) {
    const value = defaults[key]
    if (value !== null && value !== undefined) Object.assign(merged, { [key]: value })
  }
  return merged
}
export const usePreferencesStore = defineStore('preferences', {
  state: () => ({ defaults: systemDefaults(), markdown: '', loaded: false, saving: false }),
  actions: {
    async load() { const result = await api.getPreferences(); this.defaults = mergeDefinedDefaults(result.defaults); this.markdown = result.style_markdown; this.loaded = true },
    restoreSystemDefaults() { this.defaults = systemDefaults() },
    async saveDefaults() { this.saving = true; try { this.defaults = await api.saveDefaults(this.defaults) } finally { this.saving = false } },
    async saveStyle() { this.saving = true; try { await api.saveStyle(this.markdown) } finally { this.saving = false } },
    async clear() { await api.clearPreferences(); this.defaults = systemDefaults(); this.markdown = '' },
  },
})
