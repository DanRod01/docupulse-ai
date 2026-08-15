import type {
  ChatMessage,
  RAGQueryRequest,
  RAGSourceItem,
  SSEEventPayload,
} from '~/types/api'

export function useRagChat() {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBaseUrl
  const apiKey = config.public.apiKey as string

  const messages = ref<ChatMessage[]>([])
  const isStreaming = ref<boolean>(false)
  const error = ref<string | null>(null)
  const selectedDocumentId = ref<string | null>(null)
  const selectedModel = ref<string>('gemini-flash-latest')
  const vecWeight = ref<number>(0.6)
  const textWeight = ref<number>(0.4)

  function extractErrorMessage(err: unknown): string {
    if (err instanceof Error) {
      return err.message
    }
    if (typeof err === 'string') {
      return err
    }
    return 'Ocorreu um erro inesperado na comunicação com o servidor de IA.'
  }

  const sendQuery = async (queryText: string): Promise<void> => {
    const trimmed = queryText.trim()
    if (!trimmed || isStreaming.value) {
      return
    }

    error.value = null

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: trimmed,
      timestamp: new Date().toLocaleTimeString(),
    }
    messages.value.push(userMessage)

    const assistantMessageId = crypto.randomUUID()
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      sources: [],
      timestamp: new Date().toLocaleTimeString(),
      isStreaming: true,
      modelUsed: selectedModel.value,
    }
    messages.value.push(assistantMessage)
    isStreaming.value = true

    const payload: RAGQueryRequest = {
      query: trimmed,
      document_id: selectedDocumentId.value,
      model_name: selectedModel.value,
      temperature: 0.2,
      match_count: 5,
      vec_weight: vecWeight.value,
      text_weight: textWeight.value,
    }

    try {
      const response = await fetch(`${apiBase}/rag/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          'X-Api-Key': apiKey,
        },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Erro na API (${response.status}): ${errorText || response.statusText}`)
      }

      if (!response.body) {
        throw new Error('Corpo de resposta de stream não suportado pelo navegador.')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          break
        }

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmedLine = line.trim()
          if (!trimmedLine.startsWith('data:')) {
            continue
          }

          const rawData = trimmedLine.replace(/^data:\s*/, '')
          if (!rawData) {
            continue
          }

          try {
            const parsed = JSON.parse(rawData) as SSEEventPayload
            const targetMsg = messages.value.find((m) => m.id === assistantMessageId)
            if (!targetMsg) {
              continue
            }

            if (parsed.event_type === 'sources' && Array.isArray(parsed.data)) {
              targetMsg.sources = parsed.data as RAGSourceItem[]
            } else if (parsed.event_type === 'token' && typeof parsed.data === 'string') {
              targetMsg.content += parsed.data
            } else if (parsed.event_type === 'done' && typeof parsed.data === 'object') {
              targetMsg.isStreaming = false
              const doneData = parsed.data as Record<string, unknown>
              if (typeof doneData.execution_time_ms === 'number') {
                targetMsg.executionTimeMs = doneData.execution_time_ms
              }
              if (typeof doneData.model_used === 'string') {
                targetMsg.modelUsed = doneData.model_used
              }
            } else if (parsed.event_type === 'error' && typeof parsed.data === 'string') {
              error.value = parsed.data
              targetMsg.content += `\n\n⚠️ *[Erro: ${parsed.data}]*`
              targetMsg.isStreaming = false
            }
          } catch {
            // Ignora frames malformados sem quebrar a stream
          }
        }
      }
    } catch (err: unknown) {
      const errMsg = extractErrorMessage(err)
      error.value = errMsg
      const targetMsg = messages.value.find((m) => m.id === assistantMessageId)
      if (targetMsg) {
        if (!targetMsg.content) {
          targetMsg.content = `Não foi possível se comunicar com o backend: ${errMsg}`
        }
        targetMsg.isStreaming = false
      }
    } finally {
      isStreaming.value = false
      const targetMsg = messages.value.find((m) => m.id === assistantMessageId)
      if (targetMsg) {
        targetMsg.isStreaming = false
      }
    }
  }

  const clearChat = (): void => {
    messages.value = []
    error.value = null
  }

  return {
    messages,
    isStreaming,
    error,
    selectedDocumentId,
    selectedModel,
    vecWeight,
    textWeight,
    sendQuery,
    clearChat,
  }
}
