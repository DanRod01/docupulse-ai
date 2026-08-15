<script setup lang="ts">
import type {
  DocumentResponse,
  HealthCheckResponse,
  RAGSourceItem,
} from '~/types/api'
import { useRagChat } from '~/composables/useRagChat'

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

// Modais
const isSourceModalOpen = ref<boolean>(false)
const activeSource = ref<RAGSourceItem | null>(null)
const isUploadModalOpen = ref<boolean>(false)

const openSourceModal = (source: RAGSourceItem): void => {
  activeSource.value = source
  isSourceModalOpen.value = true
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
    // silently fail — poderia ter um toast aqui
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

const SUGGESTIONS = [
  'Quais são os principais dados dos documentos ingeridos?',
  'Há valores numéricos ou métricas de desempenho?',
  'Resuma os pontos mais relevantes encontrados.',
  'Existem termos ou cláusulas importantes?',
]
</script>

<template>
  <div class="h-screen bg-slate-950 text-slate-100 font-sans antialiased flex overflow-hidden">
    <!-- Glow de fundo -->
    <div class="fixed inset-0 overflow-hidden pointer-events-none z-0">
      <div class="absolute -top-60 left-1/3 w-[600px] h-[400px] bg-brand-600/8 blur-[180px] rounded-full" />
      <div class="absolute bottom-0 right-0 w-[400px] h-[400px] bg-accent-600/6 blur-[150px] rounded-full" />
    </div>

    <!-- ═══════════════════════════════════════════════
         SIDEBAR ESQUERDA
    ════════════════════════════════════════════════ -->
    <aside
      class="relative z-20 flex flex-col border-r border-slate-800/80 bg-slate-900/70 backdrop-blur-xl transition-all duration-300 flex-shrink-0"
      :class="isSidebarCollapsed ? 'w-16' : 'w-64'"
    >
      <!-- Logo -->
      <div class="flex items-center gap-3 px-4 py-4 border-b border-slate-800">
        <div class="h-8 w-8 flex-shrink-0 rounded-xl bg-gradient-to-tr from-brand-600 to-accent-500 flex items-center justify-center shadow-lg shadow-brand-500/25 font-mono font-black text-white text-xs">
          DP
        </div>
        <div v-if="!isSidebarCollapsed" class="min-w-0 animate-fade-in">
          <p class="text-sm font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-300">
            DocuPulse AI
          </p>
          <p class="text-[10px] text-slate-500 font-mono">RAG Híbrido · pgvector</p>
        </div>
        <button
          class="ml-auto flex-shrink-0 p-1 rounded-lg hover:bg-slate-800 text-slate-500 hover:text-slate-300 transition"
          @click="isSidebarCollapsed = !isSidebarCollapsed"
        >
          <svg class="w-3.5 h-3.5 transition-transform duration-300" :class="isSidebarCollapsed ? 'rotate-180' : ''" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
          </svg>
        </button>
      </div>

      <!-- Novo Upload -->
      <div class="px-3 pt-3 pb-2">
        <button
          class="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl bg-gradient-to-r from-brand-600/90 to-accent-600/90 hover:from-brand-500 hover:to-accent-500 text-white text-xs font-semibold shadow-md shadow-brand-500/20 transition"
          :class="isSidebarCollapsed ? 'justify-center' : ''"
          @click="isUploadModalOpen = true"
        >
          <svg class="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          <span v-if="!isSidebarCollapsed">Novo Documento</span>
        </button>
      </div>

      <!-- Lista de Documentos -->
      <div class="flex-1 overflow-y-auto px-2 py-2 space-y-1">
        <p v-if="!isSidebarCollapsed" class="px-2 pt-1 pb-1 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
          Base de Conhecimento ({{ documents.length }})
        </p>

        <!-- Loading skeleton -->
        <template v-if="isLoadingDocs">
          <div v-for="i in 3" :key="i" class="h-10 rounded-lg bg-slate-800/50 animate-pulse" />
        </template>

        <!-- Empty state -->
        <div
          v-else-if="documents.length === 0 && !isSidebarCollapsed"
          class="flex flex-col items-center justify-center py-8 text-center px-3"
        >
          <div class="h-10 w-10 rounded-xl bg-slate-800 flex items-center justify-center mb-2 text-lg">📂</div>
          <p class="text-[11px] text-slate-400 font-medium">Nenhum documento ainda</p>
          <p class="text-[10px] text-slate-600 mt-0.5">Faça upload para começar</p>
        </div>

        <!-- Documentos -->
        <button
          v-for="doc in documents"
          :key="doc.id"
          class="w-full group flex items-center gap-2.5 px-2 py-2 rounded-lg text-left transition-all duration-150"
          :class="selectedDocumentId === doc.id
            ? 'bg-brand-500/15 border border-brand-500/25 text-white'
            : 'hover:bg-slate-800/60 text-slate-400 hover:text-slate-200 border border-transparent'"
          @click="selectedDocumentId = selectedDocumentId === doc.id ? null : doc.id"
          :title="doc.title"
        >
          <span class="text-base flex-shrink-0">{{ fileTypeIcon(doc.file_type) }}</span>
          <div v-if="!isSidebarCollapsed" class="min-w-0 flex-1">
            <p class="text-xs font-medium truncate">{{ doc.title }}</p>
            <p class="text-[10px] text-slate-500 font-mono">{{ doc.total_chunks }} chunks</p>
          </div>
          <button
            v-if="!isSidebarCollapsed"
            class="flex-shrink-0 p-0.5 rounded opacity-0 group-hover:opacity-100 hover:text-rose-400 transition"
            @click.stop="deleteDocument(doc.id)"
            title="Remover documento"
          >
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </button>
      </div>

      <!-- Footer da Sidebar: Status do sistema -->
      <div class="px-3 py-3 border-t border-slate-800">
        <div
          class="flex items-center gap-2 px-2 py-1.5 rounded-lg"
          :class="isSidebarCollapsed ? 'justify-center' : ''"
        >
          <div
            class="h-2 w-2 rounded-full flex-shrink-0"
            :class="healthData?.environment_checks.gemini_api_key_configured && healthData?.environment_checks.database_url_configured
              ? 'bg-emerald-500 shadow-sm shadow-emerald-500/50'
              : 'bg-amber-500'"
          />
          <span v-if="!isSidebarCollapsed" class="text-[10px] text-slate-500 font-mono">
            {{ healthData?.environment_checks.gemini_api_key_configured && healthData?.environment_checks.database_url_configured
              ? 'Sistema operacional'
              : 'Configuração pendente' }}
          </span>
        </div>
      </div>
    </aside>

    <!-- ═══════════════════════════════════════════════
         ÁREA PRINCIPAL
    ════════════════════════════════════════════════ -->
    <div class="relative z-10 flex-1 flex flex-col overflow-hidden">

      <!-- Topbar -->
      <header class="flex-shrink-0 h-14 flex items-center justify-between px-5 border-b border-slate-800/80 bg-slate-900/50 backdrop-blur-sm">
        <div class="flex items-center gap-3">
          <!-- Contexto ativo -->
          <div v-if="selectedDocumentId" class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-300 text-xs font-medium">
            <div class="h-1.5 w-1.5 rounded-full bg-brand-400" />
            {{ documents.find(d => d.id === selectedDocumentId)?.title ?? 'Documento selecionado' }}
            <button class="ml-1 hover:text-white transition" @click="selectedDocumentId = null">
              <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>
          <span v-else class="text-xs text-slate-500 font-mono">
            Todos os documentos · {{ documents.length }} na base
          </span>
        </div>

        <div class="flex items-center gap-2">
          <!-- Seletor de Modelo -->
          <select
            v-model="selectedModel"
            class="px-2.5 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700 text-[11px] text-slate-300 focus:outline-none focus:border-brand-500 font-mono transition"
          >
            <option value="gemini-flash-latest">⚡ Flash</option>
            <option value="gemini-pro-latest">🧠 Pro</option>
          </select>

          <!-- Botão de configurações RAG -->
          <button
            @click="activePanel = activePanel === 'settings' ? 'chat' : 'settings'"
            class="p-2 rounded-lg transition"
            :class="activePanel === 'settings' ? 'bg-brand-500/20 text-brand-300 border border-brand-500/30' : 'hover:bg-slate-800 text-slate-400'"
            title="Configurações RAG"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
            </svg>
          </button>

          <button
            @click="clearChat"
            class="p-2 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-rose-400 transition"
            title="Limpar conversa"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </header>

      <!-- Painel de Configurações RAG (slide in) -->
      <Transition name="settings-panel">
        <div
          v-if="activePanel === 'settings'"
          class="flex-shrink-0 border-b border-slate-800 bg-slate-900/80 px-6 py-4"
        >
          <div class="flex items-start gap-8 max-w-3xl">
            <div class="flex-1 space-y-2">
              <div class="flex justify-between text-xs text-slate-400">
                <span>Semântica (vetores)</span>
                <span class="font-mono text-brand-400 font-bold">{{ (vecWeight * 100).toFixed(0) }}%</span>
              </div>
              <input v-model.number="vecWeight" type="range" min="0" max="1" step="0.05" class="w-full accent-brand-500" />
            </div>
            <div class="flex-1 space-y-2">
              <div class="flex justify-between text-xs text-slate-400">
                <span>Textual (palavras-chave)</span>
                <span class="font-mono text-accent-400 font-bold">{{ (textWeight * 100).toFixed(0) }}%</span>
              </div>
              <input v-model.number="textWeight" type="range" min="0" max="1" step="0.05" class="w-full accent-accent-500" />
            </div>
            <div class="text-[10px] text-slate-500 font-mono pt-4 flex-shrink-0">
              Algoritmo RRF (k=60)
            </div>
          </div>
        </div>
      </Transition>

      <!-- ─── ÁREA DO CHAT ─── -->
      <div ref="chatContainerRef" class="flex-1 overflow-y-auto">
        <!-- Welcome Screen -->
        <div v-if="messages.length === 0" class="h-full flex flex-col items-center justify-center px-6 py-12 text-center animate-fade-in">
          <div class="mb-6">
            <!-- Avatar DocuPulse -->
            <div class="h-16 w-16 mx-auto rounded-2xl bg-gradient-to-tr from-brand-600/40 to-accent-500/30 border border-brand-500/30 flex items-center justify-center shadow-2xl shadow-brand-500/10 mb-4">
              <svg class="w-8 h-8 text-brand-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <h2 class="text-xl font-extrabold text-white tracking-tight">DocuPulse Engine</h2>
            <p class="text-sm text-slate-400 mt-1.5 max-w-md mx-auto leading-relaxed">
              Faça perguntas sobre os seus documentos. As respostas são geradas com base em citações diretas das fontes indexadas.
            </p>
          </div>

          <!-- Sugestões de perguntas -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-w-xl w-full">
            <button
              v-for="suggestion in SUGGESTIONS"
              :key="suggestion"
              @click="userInput = suggestion; handleSendMessage()"
              class="px-4 py-3 rounded-xl bg-slate-900/80 hover:bg-slate-800 border border-slate-800 hover:border-brand-500/30 text-[12px] text-slate-300 hover:text-white text-left transition-all duration-150 group"
            >
              <div class="flex items-start gap-2">
                <svg class="w-3.5 h-3.5 text-brand-500 mt-0.5 flex-shrink-0 group-hover:text-brand-300 transition" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
                </svg>
                {{ suggestion }}
              </div>
            </button>
          </div>
        </div>

        <!-- Mensagens -->
        <div v-else class="px-4 py-6 space-y-6 max-w-4xl mx-auto w-full">
          <div
            v-for="msg in messages"
            :key="msg.id"
            class="animate-slide-up"
            :class="msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'"
          >
            <!-- Mensagem do Usuário -->
            <div
              v-if="msg.role === 'user'"
              class="max-w-[70%] px-4 py-3 rounded-2xl rounded-tr-sm bg-gradient-to-br from-brand-600 to-brand-700 text-white text-sm leading-relaxed shadow-lg shadow-brand-500/15"
            >
              {{ msg.content }}
            </div>

            <!-- Mensagem do Assistente -->
            <div v-else class="max-w-[85%] w-full">
              <div class="flex items-start gap-3">
                <!-- Avatar -->
                <div class="flex-shrink-0 h-8 w-8 rounded-xl bg-gradient-to-tr from-brand-600/30 to-accent-500/20 border border-brand-500/25 flex items-center justify-center mt-0.5">
                  <svg class="w-4 h-4 text-brand-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>

                <div class="flex-1 min-w-0 space-y-3">
                  <!-- Header da mensagem -->
                  <div class="flex items-center justify-between">
                    <span class="text-xs font-bold text-brand-300">DocuPulse Engine</span>
                    <span v-if="msg.executionTimeMs" class="text-[10px] font-mono text-slate-500">
                      {{ msg.executionTimeMs }}ms · {{ msg.modelUsed }}
                    </span>
                  </div>

                  <!-- Fontes citadas -->
                  <div v-if="msg.sources && msg.sources.length > 0" class="flex flex-wrap gap-1.5">
                    <button
                      v-for="src in msg.sources"
                      :key="src.chunk_id"
                      @click="openSourceModal(src)"
                      class="px-2.5 py-1 rounded-md bg-slate-800/80 hover:bg-slate-700 border border-slate-700 hover:border-brand-500/40 text-slate-400 hover:text-brand-300 text-[10px] font-mono flex items-center gap-1 transition"
                    >
                      <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                      Fonte {{ src.source_index }}: {{ (src.metadata.filename as string | undefined)?.split('.')[0] ?? 'Doc' }}
                    </button>
                  </div>

                  <!-- Conteúdo -->
                  <div class="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">
                    {{ msg.content }}
                    <!-- Cursor piscante durante stream -->
                    <span v-if="msg.isStreaming" class="inline-block h-4 w-0.5 bg-brand-400 ml-0.5 align-text-bottom animate-blink" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ─── INPUT ─── -->
      <div class="flex-shrink-0 border-t border-slate-800 bg-slate-900/70 backdrop-blur-sm px-4 py-4">
        <div class="max-w-4xl mx-auto">
          <div class="flex items-end gap-3">
            <div class="flex-1 relative">
              <textarea
                v-model="userInput"
                :disabled="isStreaming"
                rows="1"
                placeholder="Pergunte aos seus documentos..."
                class="w-full px-4 py-3 pr-12 rounded-xl bg-slate-800 border border-slate-700 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 disabled:opacity-50 resize-none transition leading-relaxed"
                style="min-height: 48px; max-height: 160px; overflow-y: auto;"
                @keydown="handleKeydown"
              />
            </div>
            <button
              @click="handleSendMessage"
              :disabled="!userInput.trim() || isStreaming"
              class="h-12 w-12 flex-shrink-0 rounded-xl bg-gradient-to-br from-brand-600 to-accent-600 hover:from-brand-500 hover:to-accent-500 text-white shadow-lg shadow-brand-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center justify-center"
            >
              <svg v-if="isStreaming" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
              </svg>
              <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
              </svg>
            </button>
          </div>
          <div v-if="chatError" class="mt-2 flex items-center gap-1.5 text-[11px] text-rose-400">
            <svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
            {{ chatError }}
          </div>
          <p class="mt-2 text-center text-[10px] text-slate-600">
            Enter para enviar · Shift+Enter para nova linha · As respostas são geradas com base exclusivamente nos documentos indexados
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
  transition: all 0.2s ease;
  max-height: 200px;
}
.settings-panel-enter-from,
.settings-panel-leave-to {
  opacity: 0;
  max-height: 0;
}
</style>
