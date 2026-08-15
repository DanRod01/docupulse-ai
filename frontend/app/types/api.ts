export interface EnvironmentChecks {
  gemini_api_key_configured: boolean
  database_url_configured: boolean
}

export interface HealthCheckResponse {
  status: string
  project: string
  version: string
  timestamp: string
  environment_checks: EnvironmentChecks
}

export type MetadataValue = string | number | boolean | null

export interface ChunkItem {
  chunk_index: number
  content: string
  character_count: number
  token_estimate: number
  metadata: Record<string, MetadataValue>
}

export interface TabularColumnStats {
  column_name: string
  data_type: string
  null_count: number
  unique_count: number
  mean: number | null
  min_value: string | number | null
  max_value: string | number | null
}

export interface TabularAnalyticsSummary {
  row_count: number
  column_count: number
  columns: string[]
  column_stats: TabularColumnStats[]
  sample_records: Record<string, MetadataValue>[]
}

export type DocumentStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface DocumentResponse {
  id: string
  title: string
  filename: string
  file_type: string
  file_size_bytes: number
  total_chunks: number
  status: DocumentStatus
  metadata: Record<string, MetadataValue>
  created_at: string
  updated_at: string
}

export interface DocumentUploadResponse {
  document: DocumentResponse
  chunks: ChunkItem[]
  tabular_summary?: TabularAnalyticsSummary | null
}

export interface RAGSourceItem {
  source_index: number
  chunk_id: string
  document_id: string
  chunk_index: number
  content: string
  score: number
  metadata: Record<string, MetadataValue>
}

export interface RAGQueryRequest {
  query: string
  document_id?: string | null
  model_name?: string
  temperature?: number
  match_count?: number
  vec_weight?: number
  text_weight?: number
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: RAGSourceItem[]
  timestamp: string
  isStreaming?: boolean
  modelUsed?: string
  executionTimeMs?: number
}

export interface SSEEventPayload {
  event_type: 'sources' | 'token' | 'error' | 'done'
  data: string | RAGSourceItem[] | Record<string, MetadataValue>
}

export type UploadStep = 'idle' | 'uploading' | 'extracting' | 'chunking' | 'embedding' | 'done' | 'error'
