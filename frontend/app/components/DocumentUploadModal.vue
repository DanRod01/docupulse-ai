<script setup lang="ts">
import type { ChunkItem, DocumentUploadResponse, UploadStep } from '~/types/api'

defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'uploaded', response: DocumentUploadResponse): void
}>()

const config = useRuntimeConfig()
const apiBase = config.public.apiBaseUrl
const apiKey = config.public.apiKey as string

const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const imagePreviewUrl = ref<string | null>(null)
const isImageFile = ref<boolean>(false)
const isPdfFile = ref<boolean>(false)
const customTitle = ref<string>('')
const chunkSize = ref<number>(800)
const chunkOverlap = ref<number>(150)
const autoEmbed = ref<boolean>(true)

const uploadStep = ref<UploadStep>('idle')
const error = ref<string | null>(null)
const previewChunks = ref<ChunkItem[]>([])
const isPreviewing = ref<boolean>(false)

const isUploading = computed(() => uploadStep.value !== 'idle' && uploadStep.value !== 'done' && uploadStep.value !== 'error')

const uploadStepLabel = computed<string>(() => {
  switch (uploadStep.value) {
    case 'uploading':   return 'Enviando arquivo...'
    case 'extracting':
      if (isImageFile.value) return 'Gemini Vision extraindo conteúdo da imagem...'
      if (isPdfFile.value) return 'PyMuPDF extraindo páginas e executando OCR...'
      return 'Lendo e decodificando arquivo...'
    case 'chunking':    return 'Fatiando texto em fragmentos inteligentes...'
    case 'embedding':   return 'Gerando vetores semânticos com Gemini...'
    case 'done':        return 'Documento ingerido com sucesso!'
    case 'error':       return 'Erro durante ingestão.'
    default:            return ''
  }
})

const uploadStepPercent = computed<number>(() => {
  switch (uploadStep.value) {
    case 'uploading':  return 20
    case 'extracting': return 45
    case 'chunking':   return 65
    case 'embedding':  return 85
    case 'done':       return 100
    default:           return 0
  }
})

const handleFile = (file: File): void => {
  selectedFile.value = file
  isImageFile.value = file.type.startsWith('image/') || /\.(png|jpe?g|webp|gif)$/i.test(file.name)
  isPdfFile.value = file.type === 'application/pdf' || /\.pdf$/i.test(file.name)
  if (isImageFile.value) {
    imagePreviewUrl.value = URL.createObjectURL(file)
  } else {
    imagePreviewUrl.value = null
  }
  if (!customTitle.value) {
    customTitle.value = file.name.replace(/\.[^/.]+$/, '')
  }
  error.value = null
  uploadStep.value = 'idle'
}

const onFileSelected = (event: Event): void => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    const file = target.files[0]
    if (file) handleFile(file)
  }
}

const onDropFile = (event: DragEvent): void => {
  if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
    const file = event.dataTransfer.files[0]
    if (file) handleFile(file)
  }
}

const generatePreview = async (): Promise<void> => {
  if (!selectedFile.value) return
  if (isImageFile.value || isPdfFile.value) {
    error.value = 'O preview de PDFs e imagens é processado durante a ingestão completa.'
    return
  }
  isPreviewing.value = true
  error.value = null
  try {
    const text = await selectedFile.value.text()
    const formData = new FormData()
    formData.append('text', text.substring(0, 5000))
    formData.append('chunk_size', chunkSize.value.toString())
    formData.append('chunk_overlap', chunkOverlap.value.toString())
    const chunks = await $fetch<ChunkItem[]>(`${apiBase}/documents/preview-chunks`, {
      method: 'POST',
      body: formData,
      headers: { 'X-Api-Key': apiKey },
    })
    previewChunks.value = chunks
  } catch {
    error.value = 'Não foi possível gerar o preview de fatiamento.'
  } finally {
    isPreviewing.value = false
  }
}

function extractFetchError(err: unknown): string {
  if (err && typeof err === 'object' && 'data' in err) {
    const fetchErr = err as { data?: { detail?: string } }
    if (fetchErr.data?.detail) return fetchErr.data.detail
  }
  if (err instanceof Error) return err.message
  return 'Falha no upload do documento.'
}

const closeModal = (): void => {
  if (isUploading.value) return
  selectedFile.value = null
  imagePreviewUrl.value = null
  isImageFile.value = false
  isPdfFile.value = false
  customTitle.value = ''
  previewChunks.value = []
  error.value = null
  uploadStep.value = 'idle'
  emit('close')
}

const submitUpload = async (): Promise<void> => {
  if (!selectedFile.value) {
    error.value = 'Selecione um arquivo para upload.'
    return
  }

  error.value = null
  uploadStep.value = 'uploading'

  const formData = new FormData()
  formData.append('file', selectedFile.value)
  if (customTitle.value) formData.append('title', customTitle.value)
  formData.append('chunk_size', chunkSize.value.toString())
  formData.append('chunk_overlap', chunkOverlap.value.toString())
  formData.append('auto_embed', autoEmbed.value ? 'true' : 'false')

  // Simulação de progresso visual por etapas
  const stepDelay = (step: UploadStep, ms: number) =>
    new Promise<void>((res) => setTimeout(() => { uploadStep.value = step; res() }, ms))

  try {
    const isHeavy = isImageFile.value || isPdfFile.value
    const progressPromise = isHeavy
      ? stepDelay('extracting', 600).then(() => stepDelay('chunking', 2200)).then(() => stepDelay('embedding', 3800))
      : stepDelay('extracting', 400).then(() => stepDelay('chunking', 800)).then(() => stepDelay('embedding', 1500))

    const uploadPromise = $fetch<DocumentUploadResponse>(`${apiBase}/documents/upload`, {
      method: 'POST',
      body: formData,
      headers: { 'X-Api-Key': apiKey },
    })

    const [response] = await Promise.all([uploadPromise, progressPromise])
    uploadStep.value = 'done'

    await new Promise<void>((res) => setTimeout(res, 900))
    emit('uploaded', response)
    closeModal()
  } catch (err: unknown) {
    uploadStep.value = 'error'
    error.value = extractFetchError(err)
  }
}
</script>

<template>
  <Transition name="modal">
    <div
      v-if="isOpen"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      @click.self="closeModal"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" @click="closeModal" />

      <!-- Modal -->
      <div class="relative w-full max-w-2xl bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl shadow-black/50 overflow-hidden animate-slide-up">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-slate-800">
          <div class="flex items-center gap-3">
            <div class="h-8 w-8 rounded-lg bg-brand-500/20 border border-brand-500/30 flex items-center justify-center">
              <svg class="w-4 h-4 text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <div>
              <h2 class="text-sm font-bold text-white">Ingestão de Documento</h2>
              <p class="text-[11px] text-slate-400">PDF, TXT, Markdown, CSV ou Imagens (PNG/JPG/WEBP)</p>
            </div>
          </div>
          <button
            class="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition"
            @click="closeModal"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Body -->
        <div class="p-6 space-y-5 max-h-[80vh] overflow-y-auto">
          <!-- Dropzone -->
          <div
            class="relative border-2 border-dashed rounded-xl transition-all duration-200 cursor-pointer"
            :class="selectedFile
              ? 'border-brand-500/50 bg-brand-500/5'
              : 'border-slate-700 hover:border-brand-500/40 hover:bg-slate-800/50 bg-slate-800/30'"
            @dragover.prevent
            @drop.prevent="onDropFile"
            @click="fileInputRef?.click()"
          >
            <input
              ref="fileInputRef"
              type="file"
              class="hidden"
              accept=".pdf,.txt,.md,.csv,.png,.jpg,.jpeg,.webp,.gif"
              @change="onFileSelected"
            />

            <!-- Preview de imagem selecionada -->
            <div v-if="isImageFile && imagePreviewUrl" class="flex flex-col items-center gap-3 p-5">
              <img
                :src="imagePreviewUrl"
                alt="Preview"
                class="max-h-40 rounded-lg object-contain border border-slate-700 shadow-lg"
              />
              <div class="text-center">
                <p class="text-xs font-semibold text-brand-300">{{ selectedFile?.name }}</p>
                <p class="text-[11px] text-slate-400 mt-0.5">{{ ((selectedFile?.size ?? 0) / 1024).toFixed(1) }} KB</p>
                <span class="inline-flex items-center gap-1 mt-2 px-2.5 py-0.5 rounded-full bg-accent-600/20 border border-accent-500/30 text-accent-300 text-[10px] font-semibold">
                  <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path d="M10 12a2 2 0 100-4 2 2 0 000 4z"/><path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd"/></svg>
                  Gemini Vision OCR
                </span>
              </div>
            </div>

            <!-- PDF selecionado -->
            <div v-else-if="isPdfFile" class="flex flex-col items-center gap-3 p-6 text-center">
              <div class="h-12 w-12 rounded-xl bg-rose-500/20 border border-rose-500/30 flex items-center justify-center text-2xl">
                📕
              </div>
              <div>
                <p class="text-xs font-semibold text-rose-300">{{ selectedFile?.name }}</p>
                <p class="text-[11px] text-slate-400 mt-0.5">{{ ((selectedFile?.size ?? 0) / 1024).toFixed(1) }} KB · Clique para trocar</p>
                <span class="inline-flex items-center gap-1 mt-2 px-2.5 py-0.5 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-300 text-[10px] font-semibold">
                  ⚡ PyMuPDF + OCR Híbrido
                </span>
              </div>
            </div>

            <!-- Estado padrão ou arquivo de texto selecionado -->
            <div v-else class="flex flex-col items-center gap-3 p-8 text-center">
              <div class="h-12 w-12 rounded-xl bg-slate-700/50 flex items-center justify-center">
                <svg v-if="selectedFile" class="w-6 h-6 text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <svg v-else class="w-6 h-6 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
              <div>
                <p v-if="selectedFile" class="text-xs font-semibold text-brand-300">{{ selectedFile.name }}</p>
                <p v-if="selectedFile" class="text-[11px] text-slate-400">{{ ((selectedFile.size) / 1024).toFixed(1) }} KB · Clique para trocar</p>
                <p v-else class="text-sm font-semibold text-slate-200">Arraste um arquivo ou clique para selecionar</p>
                <p v-if="!selectedFile" class="text-[11px] text-slate-500 mt-1">PDF, TXT, MD, CSV, PNG, JPG, WEBP · Máx. 20 MB</p>
              </div>
            </div>
          </div>

          <!-- Título personalizado -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-[11px] font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">Título do Documento</label>
              <input
                v-model="customTitle"
                type="text"
                placeholder="Nome do documento..."
                class="w-full px-3 py-2.5 rounded-lg bg-slate-950 border border-slate-800 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-brand-500 transition"
              />
            </div>
            <div class="flex items-end">
              <label class="flex items-center gap-2.5 cursor-pointer group">
                <div
                  class="relative w-10 h-5 rounded-full transition-colors duration-200"
                  :class="autoEmbed ? 'bg-brand-500' : 'bg-slate-700'"
                  @click="autoEmbed = !autoEmbed"
                >
                  <div
                    class="absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform duration-200"
                    :class="autoEmbed ? 'translate-x-5' : 'translate-x-0'"
                  />
                </div>
                <div>
                  <p class="text-xs font-semibold text-slate-200">Gerar Embeddings</p>
                  <p class="text-[10px] text-slate-500">Indexação vetorial com Gemini</p>
                </div>
              </label>
            </div>
          </div>

          <!-- Parâmetros de Chunking -->
          <div class="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-4">
            <p class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Parâmetros de Chunking</p>
            <div class="grid grid-cols-2 gap-6">
              <div>
                <div class="flex justify-between text-[11px] mb-2">
                  <span class="text-slate-400">Chunk Size</span>
                  <span class="font-mono text-brand-400 font-bold">{{ chunkSize }} chars</span>
                </div>
                <input v-model.number="chunkSize" type="range" min="100" max="4000" step="50" class="w-full accent-brand-500" />
              </div>
              <div>
                <div class="flex justify-between text-[11px] mb-2">
                  <span class="text-slate-400">Chunk Overlap</span>
                  <span class="font-mono text-accent-400 font-bold">{{ chunkOverlap }} chars</span>
                </div>
                <input v-model.number="chunkOverlap" type="range" min="0" max="1000" step="25" class="w-full accent-accent-500" />
              </div>
            </div>
            <button
              :disabled="!selectedFile || isImageFile || isPreviewing"
              @click="generatePreview"
              class="text-[11px] text-brand-400 hover:text-brand-300 disabled:opacity-40 disabled:cursor-not-allowed transition flex items-center gap-1"
            >
              <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              Preview de fatiamento
            </button>
          </div>

          <!-- Preview dos chunks -->
          <div v-if="previewChunks.length > 0" class="space-y-2">
            <p class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              {{ previewChunks.length }} fragmentos gerados
            </p>
            <div class="max-h-40 overflow-y-auto space-y-1.5 pr-1">
              <div
                v-for="chunk in previewChunks.slice(0, 8)"
                :key="chunk.chunk_index"
                class="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-300"
              >
                <div class="flex justify-between text-[10px] text-slate-500 mb-1">
                  <span>#{{ chunk.chunk_index + 1 }}</span>
                  <span>{{ chunk.character_count }} chars · ~{{ chunk.token_estimate }} tokens</span>
                </div>
                {{ chunk.content.substring(0, 120) }}{{ chunk.content.length > 120 ? '...' : '' }}
              </div>
            </div>
          </div>

          <!-- Barra de progresso animada -->
          <div v-if="isUploading || uploadStep === 'done'" class="space-y-2">
            <div class="flex justify-between text-[11px]">
              <span class="text-slate-300 font-medium">{{ uploadStepLabel }}</span>
              <span class="font-mono text-brand-400">{{ uploadStepPercent }}%</span>
            </div>
            <div class="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
              <div
                class="h-full rounded-full transition-all duration-700 ease-out"
                :class="uploadStep === 'done' ? 'bg-emerald-500' : 'bg-gradient-to-r from-brand-600 to-accent-500'"
                :style="{ width: `${uploadStepPercent}%` }"
              />
            </div>
          </div>

          <!-- Erro -->
          <div v-if="error" class="flex items-start gap-2 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-[11px] text-rose-300">
            <svg class="w-4 h-4 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span>{{ error }}</span>
          </div>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-between px-6 py-4 border-t border-slate-800 bg-slate-950/40">
          <button
            class="px-4 py-2 rounded-lg text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800 transition"
            @click="closeModal"
          >
            Cancelar
          </button>
          <button
            :disabled="!selectedFile || isUploading"
            @click="submitUpload"
            class="px-5 py-2 rounded-lg bg-gradient-to-r from-brand-600 to-accent-600 hover:from-brand-500 hover:to-accent-500 text-xs font-bold text-white shadow-lg shadow-brand-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center gap-2"
          >
            <svg v-if="isUploading" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
            </svg>
            <svg v-else class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" v-if="uploadStep === 'done'" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" v-else />
            </svg>
            {{ isUploading ? 'Processando...' : 'Fazer Ingestão' }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
