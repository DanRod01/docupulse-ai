<script setup lang="ts">
import type {
  DocumentResponse,
  HealthCheckResponse,
  RAGSourceItem,
} from '~/types/api'
import { useRagChat } from '~/composables/useRagChat'
import MarkdownRenderer from '~/components/MarkdownRenderer.vue'

const config = useRuntimeConfig()
const apiBase = config.public.apiBaseUrl
const apiKey = config.public.apiKey as string

// Chat Composable
const {
  messages,
  isStreaming,
  error: chatError,
  selectedDocumentId,
  selectedModel,
  vecWeight,
  textWeight,
  sendQuery,
  clearChat,
} = useRagChat()

const userInput = ref<string>('')
const chatContainerRef = ref<HTMLDivElement | null>(null)
const copiedMsgId = ref<string | null>(null)

// Modais
const isSourceModalOpen = ref<boolean>(false)
const activeSource = ref<RAGSourceItem | null>(null)
const isUploadModalOpen = ref<boolean>(false)

const openSourceModal = (source: RAGSourceItem): void => {
  activeSource.value = source
  isSourceModalOpen.value = true
}

const handleSelectSourceByNumber = (sourceIndex: number): void => {
  for (const msg of [...messages.value].reverse()) {
    if (msg.role === 'assistant' && msg.sources) {
      const match = msg.sources.find((s) => s.source_index === sourceIndex)
      if (match) {
        openSourceModal(match)
        return
      }
    }
  }
}

const copyMessageContent = async (msgId: string, content: string): Promise<void> => {
  try {
    await navigator.clipboard.writeText(content)
    copiedMsgId.value = msgId
    setTimeout(() => {
      if (copiedMsgId.value === msgId) {
        copiedMsgId.value = null
      }
    }, 2000)
  } catch {
    // Fallback silencioso
  }
}

// Sidebar e Painéis
type ActivePanel = 'chat' | 'settings'
const activePanel = ref<ActivePanel>('chat')
const isSidebarCollapsed = ref<boolean>(false)

// Documentos
const documents = ref<DocumentResponse[]>([])
const isLoadingDocs = ref<boolean>(false)

const fetchDocuments = async (): Promise<void> => {
  isLoadingDocs.value = true
  try {
    const data = await $fetch<DocumentResponse[]>(`${apiBase}/documents`, {
      headers: { 'X-Api-Key': apiKey },
    })
    documents.value = data
  } catch {
    documents.value = []
  } finally {
    isLoadingDocs.value = false
  }
}

const deleteDocument = async (id: string): Promise<void> => {
  try {
    await $fetch(`${apiBase}/documents/${id}`, {
      method: 'DELETE',
      headers: { 'X-Api-Key': apiKey },
    })
    documents.value = documents.value.filter((d) => d.id !== id)
    if (selectedDocumentId.value === id) {
      selectedDocumentId.value = null
    }
  } catch {
    // Fallback silencioso
  }
}

// Health
const healthData = ref<HealthCheckResponse | null>(null)
const checkHealth = async (): Promise<void> => {
  try {
    healthData.value = await $fetch<HealthCheckResponse>(`${apiBase}/health`, { timeout: 5000 })
  } catch {
    healthData.value = null
  }
}

const handleSendMessage = async (): Promise<void> => {
  const query = userInput.value
  if (!query.trim() || isStreaming.value) return
  userInput.value = ''
  await sendQuery(query)
}

const scrollToBottom = (): void => {
  nextTick(() => {
    if (chatContainerRef.value) {
      chatContainerRef.value.scrollTop = chatContainerRef.value.scrollHeight
    }
  })
}

watch(
  () => messages.value.map((m) => m.content).join(''),
  () => scrollToBottom()
)

const handleKeydown = (e: KeyboardEvent): void => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSendMessage()
  }
}

onMounted(() => {
  checkHealth()
  fetchDocuments()
})

const fileTypeIcon = (fileType: string): string => {
  if (fileType.includes('pdf') || fileType.endsWith('.pdf')) return '📕'
  if (fileType.startsWith('image/')) return '🖼️'
  if (fileType.includes('csv')) return '📊'
  if (fileType.includes('markdown')) return '📝'
  return '📄'
}

const TECH_PILLARS = [
  {
    icon: '⚡',
    title: 'RAG Híbrido com RRF',
    desc: 'Combina busca semântica vetorial e Full-Text Search via Reciprocal Rank Fusion.',
  },
  {
    icon: '👁️',
    title: 'OCR Multimodal Gemini',
    desc: 'Extrai dados de balancetes, notas fiscais e imagens convertendo em tabelas estruturadas.',
  },
  {
    icon: '🗄️',
    title: 'PostgreSQL & pgvector',
    desc: 'Indexação vetorial HNSW de 768 dimensões com armazenamento transacional ACID.',
  },
  {
    icon: '🌊',
    title: 'Streaming SSE Assíncrono',
    desc: 'Geração token a token em tempo real com baixa latência e citações rastreáveis.',
  },
]

const SUGGESTIONS = [
  {
    category: '📊 Análise Financeira',
    text: 'Quais são os principais dados e saldos dos documentos ingeridos?',
  },
  {
    category: '💰 Receitas vs Despesas',
    text: 'Qual é o total geral de entradas/receitas versus despesas e o saldo final?',
  },
  {
    category: '📋 Resumo Executivo',
    text: 'Faça um resumo executivo com os principais tópicos e métricas encontradas.',
  },
  {
    category: '🔍 Auditoria de Contas',
    text: 'Quais serviços de terceiros e retenções de impostos foram registrados?',
  },
]
</script>

<template>
  <div class="h-screen bg-slate-950 text-slate-100 font-sans antialiased flex overflow-hidden selection:bg-brand-500 selection:text-white">
    <!-- Glows de fundo corporativo -->
    <div class="fixed inset-0 overflow-hidden pointer-events-none z-0">
      <div class="absolute -top-40 left-1/4 w-[700px] h-[500px] bg-brand-600/10 blur-[180px] rounded-full" />
      <div class="absolute -bottom-40 right-10 w-[500px] h-[500px] bg-accent-600/8 blur-[160px] rounded-full" />
    </div>

    <!-- ═══════════════════════════════════════════════
         SIDEBAR ESQUERDA
    ════════════════════════════════════════════════ -->
    <aside
      class="relative z-20 flex flex-col border-r border-slate-800/80 bg-slate-900/80 backdrop-blur-2xl transition-all duration-300 flex-shrink-0"
      :class="isSidebarCollapsed ? 'w-16' : 'w-72'"
    >
      <!-- Logo & Branding -->
      <div class="flex items-center gap-3 px-4 py-4 border-b border-slate-800/90">
        <div class="h-9 w-9 flex-shrink-0 rounded-xl bg-gradient-to-tr from-brand-600 via-brand-500 to-accent-500 flex items-center justify-center shadow-lg shadow-brand-500/25 font-mono font-black text-white text-xs border border-white/10">
          DP
        </div>
        <div v-if="!isSidebarCollapsed" class="min-w-0 animate-fade-in">
          <div class="flex items-center gap-1.5">
            <h1 class="text-sm font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-100 to-slate-300">
              DocuPulse AI
            </h1>
            <span class="px-1.5 py-0.2 rounded bg-brand-500/20 text-brand-300 border border-brand-500/30 text-[9px] font-mono font-bold">RAG</span>
          </div>
          <p class="text-[10px] text-slate-400 font-mono mt-0.5">Hybrid Engine · pgvector</p>
        </div>
        <button
          class="ml-auto flex-shrink-0 p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition"
          @click="isSidebarCollapsed = !isSidebarCollapsed"
          title="Recolher menu lateral"
        >
          <svg class="w-4 h-4 transition-transform duration-300" :class="isSidebarCollapsed ? 'rotate-180' : ''" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
          </svg>
        </button>
      </div>

      <!-- Botão Novo Documento -->
      <div class="px-3 pt-3.5 pb-2">
        <button
          class="w-full flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl bg-gradient-to-r from-brand-600 to-accent-600 hover:from-brand-500 hover:to-accent-500 text-white text-xs font-bold shadow-lg shadow-brand-500/25 border border-white/10 transition-all duration-200 active:scale-[0.98]"
          :class="isSidebarCollapsed ? 'justify-center px-0' : ''"
          @click="isUploadModalOpen = true"
        >
          <svg class="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          <span v-if="!isSidebarCollapsed">Ingerir Documento</span>
        </button>
      </div>

      <!-- Lista de Documentos Ingeridos -->
      <div class="flex-1 overflow-y-auto px-2.5 py-2 space-y-1.5">
        <div v-if="!isSidebarCollapsed" class="flex items-center justify-between px-2 pt-1 pb-1">
          <p class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
            Base de Conhecimento
          </p>
          <span class="px-2 py-0.5 rounded-full bg-slate-800 text-[10px] font-mono text-brand-300 font-semibold border border-slate-700">
            {{ documents.length }}
          </span>
        </div>

        <!-- Skeleton de Loading -->
        <template v-if="isLoadingDocs">
          <div v-for="i in 3" :key="i" class="h-12 rounded-xl bg-slate-800/40 animate-pulse border border-slate-800/60" />
        </template>

        <!-- Empty state -->
        <div
          v-else-if="documents.length === 0 && !isSidebarCollapsed"
          class="flex flex-col items-center justify-center py-10 text-center px-4 rounded-xl border border-dashed border-slate-800 bg-slate-900/40 my-2"
        >
          <div class="h-11 w-11 rounded-2xl bg-slate-800/80 border border-slate-700 flex items-center justify-center mb-2.5 text-xl">
            📂
          </div>
          <p class="text-xs text-slate-300 font-semibold">Nenhum documento</p>
          <p class="text-[11px] text-slate-500 mt-1">Faça upload de PDFs, imagens ou planilhas para iniciar.</p>
        </div>

        <!-- Cards de Documentos -->
        <div
          v-for="doc in documents"
          :key="doc.id"
          class="w-full group relative rounded-xl border transition-all duration-200 cursor-pointer overflow-hidden"
          :class="selectedDocumentId === doc.id
            ? 'bg-brand-500/15 border-brand-500/40 shadow-lg shadow-brand-500/10'
            : 'bg-slate-900/50 hover:bg-slate-800/60 border-slate-800/80 hover:border-slate-700'"
          @click="selectedDocumentId = selectedDocumentId === doc.id ? null : doc.id"
        >
          <div class="flex items-center gap-3 p-2.5">
            <span class="text-lg flex-shrink-0 p-1 rounded-lg bg-slate-800/80 border border-slate-700/60">
              {{ fileTypeIcon(doc.file_type) }}
            </span>
            <div v-if="!isSidebarCollapsed" class="min-w-0 flex-1">
              <p class="text-xs font-semibold text-slate-200 truncate group-hover:text-white transition">
                {{ doc.title }}
              </p>
              <div class="flex items-center gap-2 mt-1">
                <span class="text-[10px] text-brand-300 font-mono font-medium">
                  {{ doc.total_chunks }} chunks
                </span>
                <span class="text-[10px] text-slate-500">•</span>
                <span class="text-[10px] text-slate-400 font-mono">
                  {{ ((doc.file_size_bytes || 0) / 1024).toFixed(0) }} KB
                </span>
                <span v-if="doc.status === 'completed'" class="ml-auto inline-flex items-center px-1.5 py-0.2 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[9px] font-mono font-medium">
                  Indexado
                </span>
              </div>
            </div>

            <!-- Botão de Deletar -->
            <button
              v-if="!isSidebarCollapsed"
              class="flex-shrink-0 p-1.5 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-rose-500/20 text-slate-400 hover:text-rose-300 transition border border-transparent hover:border-rose-500/30"
              @click.stop="deleteDocument(doc.id)"
              title="Remover documento"
            >
              <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- Footer da Sidebar: Status do Sistema -->
      <div class="px-3.5 py-3 border-t border-slate-800/90 bg-slate-950/40">
        <div
          class="flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800/80"
          :class="isSidebarCollapsed ? 'justify-center px-0' : ''"
        >
          <span class="relative flex h-2.5 w-2.5">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500 shadow-sm shadow-emerald-500/50" />
          </span>
          <div v-if="!isSidebarCollapsed" class="min-w-0 flex-1">
            <p class="text-[11px] font-semibold text-slate-200">PostgreSQL + Gemini</p>
            <p class="text-[9px] text-slate-400 font-mono">Conectado & Operacional</p>
          </div>
        </div>
      </div>
    </aside>

    <!-- ═══════════════════════════════════════════════
         ÁREA PRINCIPAL DE CHAT
    ════════════════════════════════════════════════ -->
    <div class="relative z-10 flex-1 flex flex-col overflow-hidden bg-slate-950/60">

      <!-- Topbar Header -->
      <header class="flex-shrink-0 h-14 flex items-center justify-between px-6 border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-xl">
        <div class="flex items-center gap-3">
          <!-- Filtro de Contexto Ativo -->
          <div
            v-if="selectedDocumentId"
            class="flex items-center gap-2 px-3 py-1 rounded-full bg-brand-500/15 border border-brand-500/30 text-brand-300 text-xs font-semibold shadow-sm"
          >
            <span class="h-1.5 w-1.5 rounded-full bg-brand-400 animate-pulse" />
            <span class="max-w-[200px] truncate">
              {{ documents.find(d => d.id === selectedDocumentId)?.title ?? 'Documento selecionado' }}
            </span>
            <button
              class="ml-1 p-0.5 rounded-full hover:bg-brand-500/30 text-brand-300 hover:text-white transition"
              @click="selectedDocumentId = null"
              title="Remover filtro de documento"
            >
              <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div v-else class="flex items-center gap-2">
            <span class="h-2 w-2 rounded-full bg-brand-500" />
            <span class="text-xs font-semibold text-slate-300">
              Base de Conhecimento Global
            </span>
            <span class="text-[11px] text-slate-500 font-mono">
              ({{ documents.length }} docs indexados)
            </span>
          </div>
        </div>

        <!-- Seletor de Modelo e Ações de Cabeçalho -->
        <div class="flex items-center gap-2.5">
          <!-- Seletor do Gemini -->
          <div class="relative flex items-center">
            <select
              v-model="selectedModel"
              class="appearance-none pl-3 pr-8 py-1.5 rounded-xl bg-slate-800/90 border border-slate-700/80 text-xs font-medium text-slate-200 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition shadow-sm cursor-pointer"
            >
              <option value="gemini-3.5-flash-lite">⚡ Gemini 3.5 Flash-Lite (Ultrarrápido)</option>
              <option value="gemini-3.5-flash">⚡ Gemini 3.5 Flash (Avançado)</option>
              <option value="gemini-3.7-flash">🧠 Gemini 3.7 Flash (Raciocínio Profundo)</option>
            </select>
            <svg class="w-3.5 h-3.5 text-slate-400 absolute right-2.5 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </div>

          <!-- Botão de Ajuste RRF -->
          <button
            @click="activePanel = activePanel === 'settings' ? 'chat' : 'settings'"
            class="p-2 rounded-xl transition border"
            :class="activePanel === 'settings'
              ? 'bg-brand-500/20 text-brand-300 border-brand-500/40 shadow-sm'
              : 'hover:bg-slate-800 text-slate-400 hover:text-white border-transparent'"
            title="Ajustar Pesos da Busca Híbrida (RRF)"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
            </svg>
          </button>

          <!-- Limpar Conversa -->
          <button
            @click="clearChat"
            class="p-2 rounded-xl hover:bg-slate-800 text-slate-400 hover:text-rose-400 transition"
            title="Limpar histórico de chat"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </header>

      <!-- Painel Gaveta de Configuração RAG (RRF Weights) -->
      <Transition name="settings-panel">
        <div
          v-if="activePanel === 'settings'"
          class="flex-shrink-0 border-b border-slate-800 bg-slate-900/95 backdrop-blur-xl px-8 py-5 shadow-2xl"
        >
          <div class="max-w-4xl mx-auto flex items-center gap-10">
            <div class="flex-1 space-y-2">
              <div class="flex justify-between text-xs font-semibold">
                <span class="text-slate-300">Peso Semântico (Vetor Cosseno pgvector)</span>
                <span class="font-mono text-brand-400 font-bold text-sm">{{ (vecWeight * 100).toFixed(0) }}%</span>
              </div>
              <input v-model.number="vecWeight" type="range" min="0" max="1" step="0.05" class="w-full accent-brand-500 cursor-pointer" />
            </div>

            <div class="flex-1 space-y-2">
              <div class="flex justify-between text-xs font-semibold">
                <span class="text-slate-300">Peso Textual (Full-Text Search tsvector)</span>
                <span class="font-mono text-accent-400 font-bold text-sm">{{ (textWeight * 100).toFixed(0) }}%</span>
              </div>
              <input v-model.number="textWeight" type="range" min="0" max="1" step="0.05" class="w-full accent-accent-500 cursor-pointer" />
            </div>

            <div class="text-[11px] text-slate-400 font-mono pt-3 border-l border-slate-800 pl-6 flex-shrink-0">
              <p class="font-bold text-white">Algoritmo RRF</p>
              <p class="text-[10px] text-slate-500 mt-0.5">k = 60 · Fusão de Ranks</p>
            </div>
          </div>
        </div>
      </Transition>

      <!-- ─── CONTAINER DE MENSAGENS / FEED ─── -->
      <div ref="chatContainerRef" class="flex-1 overflow-y-auto px-4 sm:px-6 py-6 scroll-smooth">
        <!-- WELCOME / SHOWCASE SCREEN (QUANDO NÃO HÁ MENSAGENS) -->
        <div v-if="messages.length === 0" class="min-h-full flex flex-col items-center justify-center max-w-4xl mx-auto py-8 animate-fade-in">
          <!-- Hero Header -->
          <div class="text-center space-y-3 mb-8">
            <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-500/10 border border-brand-500/25 text-brand-300 text-xs font-semibold shadow-lg shadow-brand-500/10">
              <span class="flex h-2 w-2 rounded-full bg-brand-400 animate-pulse" />
              DocuPulse AI · Hybrid RAG & Multimodal Intelligence
            </div>

            <h2 class="text-3xl sm:text-4xl font-black text-white tracking-tight leading-tight">
              Motor de Inteligência e RAG Multimodal
            </h2>

            <p class="text-sm text-slate-400 max-w-2xl mx-auto leading-relaxed">
              Consulte relatórios, balancetes financeiros, notas fiscais e PDFs digitalizados com precisão factual garantida por citações em fontes indexadas.
            </p>
          </div>

          <!-- 4 Pilares Arquiteturais (Showcase para Recrutadores) -->
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 w-full mb-8">
            <div
              v-for="pillar in TECH_PILLARS"
              :key="pillar.title"
              class="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 hover:border-brand-500/40 hover:bg-slate-900/90 transition-all duration-200 shadow-md group"
            >
              <div class="h-9 w-9 rounded-xl bg-slate-800 flex items-center justify-center text-lg mb-2.5 group-hover:scale-110 transition-transform">
                {{ pillar.icon }}
              </div>
              <h3 class="text-xs font-bold text-white group-hover:text-brand-300 transition">
                {{ pillar.title }}
              </h3>
              <p class="text-[11px] text-slate-400 mt-1 leading-relaxed">
                {{ pillar.desc }}
              </p>
            </div>
          </div>

          <!-- Sugestões de Perguntas Estruturadas -->
          <div class="w-full">
            <p class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 text-center">
              Perguntas Rápidas de Demonstração
            </p>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full">
              <button
                v-for="item in SUGGESTIONS"
                :key="item.text"
                @click="userInput = item.text; handleSendMessage()"
                class="p-3.5 rounded-2xl bg-slate-900/70 hover:bg-slate-800 border border-slate-800 hover:border-brand-500/50 text-left transition-all duration-150 group shadow-sm hover:shadow-brand-500/10 active:scale-[0.99]"
              >
                <p class="text-[10px] font-bold text-brand-400 uppercase tracking-wider mb-1">
                  {{ item.category }}
                </p>
                <div class="flex items-center justify-between gap-2">
                  <span class="text-xs font-semibold text-slate-200 group-hover:text-white transition leading-snug">
                    {{ item.text }}
                  </span>
                  <svg class="w-4 h-4 text-slate-500 group-hover:text-brand-300 group-hover:translate-x-0.5 transition-all flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </div>
              </button>
            </div>
          </div>
        </div>

        <!-- MENSAGENS EM CHAT -->
        <div v-else class="space-y-6 max-w-4xl mx-auto w-full pb-6">
          <div
            v-for="msg in messages"
            :key="msg.id"
            class="animate-slide-up"
            :class="msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'"
          >
            <!-- 👤 MENSAGEM DO USUÁRIO -->
            <div
              v-if="msg.role === 'user'"
              class="max-w-[80%] px-5 py-3.5 rounded-3xl rounded-tr-md bg-gradient-to-r from-brand-600 to-indigo-600 text-white text-sm font-medium leading-relaxed shadow-xl shadow-brand-600/20 border border-white/10"
            >
              {{ msg.content }}
            </div>

            <!-- 🤖 MENSAGEM DO ASSISTENTE (DOCUPULSE ENGINE) -->
            <div v-else class="w-full">
              <div class="p-6 rounded-3xl bg-slate-900/80 border border-slate-800/90 shadow-2xl shadow-black/40 space-y-4">
                <!-- Header da Mensagem com Badges e Ações -->
                <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/70 pb-3.5">
                  <div class="flex items-center gap-3">
                    <div class="h-8 w-8 rounded-xl bg-gradient-to-tr from-brand-600 to-accent-500 flex items-center justify-center shadow-md shadow-brand-500/20 text-white font-mono font-black text-xs">
                      DP
                    </div>
                    <div>
                      <div class="flex items-center gap-2">
                        <span class="text-xs font-bold text-white">DocuPulse Engine</span>
                        <span class="px-2 py-0.5 rounded-full bg-brand-500/15 border border-brand-500/30 text-brand-300 text-[10px] font-mono font-semibold">
                          {{ msg.modelUsed || selectedModel }}
                        </span>
                      </div>
                      <p v-if="msg.executionTimeMs" class="text-[10px] font-mono text-slate-400 mt-0.5">
                        ⏱️ Latência de resposta: <strong class="text-brand-300">{{ msg.executionTimeMs }}ms</strong>
                      </p>
                    </div>
                  </div>

                  <!-- Botão de Copiar Resposta Completa -->
                  <button
                    @click="copyMessageContent(msg.id, msg.content)"
                    class="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800/90 hover:bg-slate-700/90 border border-slate-700 text-xs text-slate-300 hover:text-white transition shadow-sm"
                    title="Copiar resposta formatada"
                  >
                    <svg v-if="copiedMsgId === msg.id" class="w-3.5 h-3.5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                    <svg v-else class="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    <span class="text-[11px] font-semibold font-mono">
                      {{ copiedMsgId === msg.id ? 'Copiado!' : 'Copiar' }}
                    </span>
                  </button>
                </div>

                <!-- Fontes Rastreáveis Citadas (Badges no topo da resposta) -->
                <div v-if="msg.sources && msg.sources.length > 0" class="space-y-1.5">
                  <p class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    Fontes Consultadas ({{ msg.sources.length }})
                  </p>
                  <div class="flex flex-wrap gap-2">
                    <button
                      v-for="src in msg.sources"
                      :key="src.chunk_id"
                      @click="openSourceModal(src)"
                      class="px-3 py-1.5 rounded-xl bg-slate-950/80 hover:bg-brand-500/10 border border-slate-800 hover:border-brand-500/40 text-slate-300 hover:text-brand-300 text-xs font-mono flex items-center gap-2 transition shadow-sm group cursor-pointer"
                    >
                      <span class="flex h-2 w-2 rounded-full bg-brand-400 group-hover:scale-125 transition-transform" />
                      <span class="font-bold text-brand-300">Fonte {{ src.source_index }}:</span>
                      <span class="text-slate-400 group-hover:text-slate-200 truncate max-w-[140px]">
                        {{ (src.metadata.filename as string | undefined) ?? 'Documento' }}
                      </span>
                      <span class="text-[10px] text-slate-500 font-normal">
                        (score {{ src.score.toFixed(3) }})
                      </span>
                    </button>
                  </div>
                </div>

                <!-- Renderizador Rico de Markdown com Tabelas e Citações Interativas -->
                <div class="relative pt-1">
                  <MarkdownRenderer
                    :content="msg.content"
                    :is-streaming="msg.isStreaming"
                    @select-source="handleSelectSourceByNumber"
                  />
                  <!-- Cursor de Streaming Animado -->
                  <span
                    v-if="msg.isStreaming"
                    class="inline-block h-4 w-1.5 bg-gradient-to-t from-brand-500 to-accent-400 rounded-sm ml-1 animate-pulse align-middle"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ─── BARRA DE ENTRADA / INPUT FIXA ─── -->
      <div class="flex-shrink-0 border-t border-slate-800/80 bg-slate-900/80 backdrop-blur-2xl px-4 sm:px-6 py-4">
        <div class="max-w-4xl mx-auto">
          <div class="flex items-end gap-3">
            <div class="flex-1 relative">
              <textarea
                v-model="userInput"
                :disabled="isStreaming"
                rows="1"
                placeholder="Faça uma pergunta sobre os documentos..."
                class="w-full px-5 py-3.5 pr-14 rounded-2xl bg-slate-800/90 border border-slate-700/80 text-sm text-white placeholder-slate-400 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 disabled:opacity-50 resize-none transition leading-relaxed shadow-inner"
                style="min-height: 52px; max-height: 180px; overflow-y: auto;"
                @keydown="handleKeydown"
              />
            </div>
            <button
              @click="handleSendMessage"
              :disabled="!userInput.trim() || isStreaming"
              class="h-[52px] w-[52px] flex-shrink-0 rounded-2xl bg-gradient-to-r from-brand-600 to-accent-600 hover:from-brand-500 hover:to-accent-500 text-white shadow-xl shadow-brand-500/25 border border-white/10 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200 active:scale-95 flex items-center justify-center"
            >
              <svg v-if="isStreaming" class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
              </svg>
              <svg v-else class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
              </svg>
            </button>
          </div>

          <!-- Banner de Erro em caso de falha -->
          <div v-if="chatError" class="mt-2.5 flex items-center gap-2 p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300">
            <svg class="w-4 h-4 flex-shrink-0 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
            </svg>
            <span>{{ chatError }}</span>
          </div>

          <p class="mt-2 text-center text-[10px] text-slate-500 font-mono">
            Pressione <kbd class="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">Enter</kbd> para enviar · <kbd class="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">Shift+Enter</kbd> para nova linha · RAG Híbrido com pgvector & Gemini
          </p>
        </div>
      </div>
    </div>

    <!-- Modais -->
    <DocumentUploadModal
      :is-open="isUploadModalOpen"
      @close="isUploadModalOpen = false"
      @uploaded="fetchDocuments"
    />

    <SourceModal
      :is-open="isSourceModalOpen"
      :source="activeSource"
      @close="isSourceModalOpen = false"
    />
  </div>
</template>

<style scoped>
.settings-panel-enter-active,
.settings-panel-leave-active {
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  max-height: 250px;
}
.settings-panel-enter-from,
.settings-panel-leave-to {
  opacity: 0;
  max-height: 0;
  transform: translateY(-8px);
}
</style>
