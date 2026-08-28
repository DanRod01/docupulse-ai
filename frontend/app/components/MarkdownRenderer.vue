<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps<{
  content: string
  isStreaming?: boolean
}>()

const emit = defineEmits<{
  (e: 'select-source', sourceIndex: number): void
}>()

// Configuração do Marked para GFM (GitHub Flavored Markdown)
marked.setOptions({
  gfm: true,
  breaks: true,
})

const renderedHtml = computed<string>(() => {
  if (!props.content) return ''

  try {
    let rawHtml = marked.parse(props.content) as string

    // 1. Envolver tabelas em um container responsivo com scroll horizontal
    rawHtml = rawHtml.replace(
      /<table>/g,
      '<div class="table-wrapper my-4 overflow-x-auto rounded-xl border border-slate-800/80 bg-slate-950/60 shadow-xl shadow-black/20"><table class="w-full text-left text-xs text-slate-300 border-collapse">'
    )
    rawHtml = rawHtml.replace(/<\/table>/g, '</table></div>')

    // 2. Estilizar cabeçalhos e células de tabela
    rawHtml = rawHtml.replace(
      /<thead>/g,
      '<thead class="bg-slate-900/90 text-[11px] font-bold uppercase tracking-wider text-slate-200 border-b border-slate-800">'
    )
    rawHtml = rawHtml.replace(
      /<th/g,
      '<th class="px-4 py-3 font-semibold text-slate-200 border-r border-slate-800/50 last:border-r-0"'
    )
    rawHtml = rawHtml.replace(
      /<td/g,
      '<td class="px-4 py-2.5 border-b border-slate-800/40 border-r border-slate-800/30 last:border-r-0 transition-colors"'
    )

    // 3. Transformar referências [Fonte X] em Badges Interativos Clicáveis
    rawHtml = rawHtml.replace(
      /\[Fonte\s*(\d+)\]/gi,
      (match, p1) =>
        `<button type="button" class="citation-badge inline-flex items-center gap-1 mx-1 px-2 py-0.5 rounded-md bg-brand-500/15 hover:bg-brand-500/30 border border-brand-500/30 hover:border-brand-500/60 text-brand-300 hover:text-white font-mono text-[11px] font-semibold transition-all duration-150 shadow-sm cursor-pointer align-baseline" data-source-index="${p1}" title="Clique para ver o trecho original"><svg class="w-2.5 h-2.5 text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>Fonte ${p1}</button>`
    )

    // 4. Estilização de Títulos
    rawHtml = rawHtml.replace(
      /<h1/g,
      '<h1 class="text-lg font-black text-white mt-4 mb-2 tracking-tight flex items-center gap-2"'
    )
    rawHtml = rawHtml.replace(
      /<h2/g,
      '<h2 class="text-base font-extrabold text-white mt-4 mb-2 tracking-tight border-b border-slate-800/60 pb-1 flex items-center gap-2"'
    )
    rawHtml = rawHtml.replace(
      /<h3/g,
      '<h3 class="text-sm font-bold text-brand-300 mt-3 mb-1.5 tracking-tight flex items-center gap-1.5"'
    )

    // 5. Estilização de Listas
    rawHtml = rawHtml.replace(/<ul/g, '<ul class="space-y-1.5 my-2.5 pl-5 list-disc marker:text-brand-400 text-slate-300"')
    rawHtml = rawHtml.replace(/<ol/g, '<ol class="space-y-1.5 my-2.5 pl-5 list-decimal marker:text-accent-400 font-medium text-slate-300"')
    rawHtml = rawHtml.replace(/<li/g, '<li class="leading-relaxed"')

    // 6. Blockquotes / Notas
    rawHtml = rawHtml.replace(
      /<blockquote/g,
      '<blockquote class="my-3 pl-3.5 py-1.5 border-l-2 border-brand-500 bg-brand-500/5 rounded-r-lg text-slate-300 italic text-xs"'
    )

    // 7. Código Inline e Blocos
    rawHtml = rawHtml.replace(
      /<code>(?!(?:(?!<\/pre>).)*$)/g,
      '<code class="px-1.5 py-0.5 rounded bg-slate-800/90 text-brand-300 font-mono text-[11px] border border-slate-700/60">'
    )

    return rawHtml
  } catch {
    return props.content
  }
})

// Delegação de eventos de clique limpa e performática (sem listeners redundantes)
const handleContainerClick = (event: MouseEvent): void => {
  const target = event.target as HTMLElement | null
  if (!target) return

  const badge = target.closest('button.citation-badge')
  if (badge) {
    const idxStr = badge.getAttribute('data-source-index')
    if (idxStr) {
      const idx = parseInt(idxStr, 10)
      if (!isNaN(idx)) {
        emit('select-source', idx)
      }
    }
  }
}
</script>

<template>
  <div
    class="markdown-content text-sm text-slate-200 leading-relaxed break-words"
    @click="handleContainerClick"
    v-html="renderedHtml"
  />
</template>

<style scoped>
:deep(.markdown-content p) {
  margin-bottom: 0.65rem;
  line-height: 1.65;
}

:deep(.markdown-content p:last-child) {
  margin-bottom: 0;
}

:deep(.markdown-content strong) {
  color: #ffffff;
  font-weight: 700;
}

:deep(.markdown-content hr) {
  border-color: rgba(51, 65, 85, 0.6);
  margin: 1rem 0;
}

:deep(.table-wrapper table tbody tr) {
  transition: background-color 0.15s ease;
}

:deep(.table-wrapper table tbody tr:nth-child(even)) {
  background-color: rgba(15, 23, 42, 0.4);
}

:deep(.table-wrapper table tbody tr:nth-child(odd)) {
  background-color: rgba(2, 6, 23, 0.6);
}

:deep(.table-wrapper table tbody tr:hover) {
  background-color: rgba(99, 102, 241, 0.08);
}

:deep(.table-wrapper table td) {
  font-feature-settings: 'tnum';
  font-variant-numeric: tabular-nums;
}

:deep(.citation-badge:hover) {
  transform: translateY(-1px);
}
</style>
