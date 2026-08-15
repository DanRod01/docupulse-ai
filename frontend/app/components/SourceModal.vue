<script setup lang="ts">
import type { RAGSourceItem } from '~/types/api'

defineProps<{
  source: RAGSourceItem | null
  isOpen: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()
</script>

<template>
  <Teleport to="body">
    <div
      v-if="isOpen && source"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md transition-opacity"
      @click.self="emit('close')"
    >
      <div class="relative w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <!-- Header do Modal -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60">
          <div class="flex items-center gap-3">
            <span class="px-2.5 py-1 rounded-lg bg-brand-500/10 text-brand-400 text-xs font-mono font-bold border border-brand-500/20">
              Fonte {{ source.source_index }}
            </span>
            <div>
              <h3 class="text-sm font-bold text-white">
                {{ source.metadata.filename || 'Documento' }}
              </h3>
              <p class="text-[11px] font-mono text-slate-400">
                Chunk #{{ source.chunk_index }} • Relevância RRF: {{ source.score.toFixed(4) }}
              </p>
            </div>
          </div>
          <button
            @click="emit('close')"
            class="h-8 w-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            ✕
          </button>
        </div>

        <!-- Conteúdo do Chunk -->
        <div class="p-6 max-h-[60vh] overflow-y-auto space-y-4 font-mono text-xs">
          <div class="p-4 rounded-xl bg-slate-950 border border-slate-800/80 text-slate-200 leading-relaxed whitespace-pre-wrap selection:bg-brand-500 selection:text-white">
            {{ source.content }}
          </div>

          <!-- Metadados Adicionais -->
          <div class="p-3 rounded-lg bg-slate-950/50 border border-slate-800 text-[11px] text-slate-400 space-y-1">
            <p><span class="text-slate-500">Chunk ID:</span> {{ source.chunk_id }}</p>
            <p><span class="text-slate-500">Document ID:</span> {{ source.document_id }}</p>
          </div>
        </div>

        <!-- Rodapé do Modal -->
        <div class="px-6 py-3 border-t border-slate-800 bg-slate-950/40 flex justify-end">
          <button
            @click="emit('close')"
            class="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 transition"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
