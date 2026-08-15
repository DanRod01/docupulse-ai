-- ==============================================================================
-- DocuPulse AI - Initial Database Schema & Hybrid Search Function
-- Migration: 001_initial_schema.sql
-- ==============================================================================

-- 1. Habilitar a extensão pgvector para armazenamento e busca vetorial
create extension if not exists vector;

-- 2. Tabela de Documentos Mestres
-- Armazena os metadados dos arquivos ingeridos (PDFs, planilhas, relatórios, imagens)
create table if not exists documents (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    filename text not null,
    file_type text not null,
    file_size_bytes bigint not null,
    total_chunks int default 0,
    status text not null default 'pending' check (status in ('pending', 'processing', 'completed', 'failed')),
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- 3. Tabela de Fragmentos (Chunks)
-- Armazena os blocos de texto, seus embeddings do Gemini (768 dimensões) e índice textual
create table if not exists document_chunks (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references documents(id) on delete cascade,
    chunk_index int not null,
    content text not null,
    -- 768 dimensões geradas pelo Google Gemini text-embedding-004
    embedding vector(768),
    -- Coluna gerada automaticamente para Full-Text Search (FTS) com suporte ao português
    fts tsvector generated always as (to_tsvector('portuguese', content)) stored,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

-- 4. Índices de Alta Performance
-- 4.1 Índice HNSW para busca semântica aproximada por distância de cosseno (<=>)
create index if not exists idx_chunks_embedding_hnsw 
on document_chunks 
using hnsw (embedding vector_cosine_ops)
with (m = 16, ef_construction = 64);

-- 4.2 Índice GIN para busca textual Full-Text ultra-rápida
create index if not exists idx_chunks_fts 
on document_chunks 
using gin (fts);

-- 4.3 Índice de chave estrangeira para deleções e consultas por documento
create index if not exists idx_chunks_document_id 
on document_chunks (document_id);

-- 5. Função de Busca Híbrida com Fusão Recíproca de Ranks (RRF - Reciprocal Rank Fusion)
create or replace function hybrid_search_chunks(
    query_text text,
    query_embedding vector(768),
    match_count int default 5,
    rrf_k int default 60,
    vec_weight float default 0.6,
    text_weight float default 0.4
)
returns table (
    id uuid,
    document_id uuid,
    chunk_index int,
    content text,
    metadata jsonb,
    combined_score float
)
language sql
as $$
with 
-- Busca Semântica: Ordena por similaridade de cosseno
vector_search as (
    select 
        id,
        row_number() over (order by embedding <=> query_embedding) as rank_vec
    from document_chunks
    where embedding is not null
    order by embedding <=> query_embedding
    limit match_count * 2
),
-- Busca Textual: Ordena por relevância textual com ts_rank_cd
text_search as (
    select 
        id,
        row_number() over (order by ts_rank_cd(fts, plainto_tsquery('portuguese', query_text)) desc) as rank_text
    from document_chunks
    where fts @@ plainto_tsquery('portuguese', query_text)
    order by ts_rank_cd(fts, plainto_tsquery('portuguese', query_text)) desc
    limit match_count * 2
)
-- Fusão dos dois ranks pelo algoritmo RRF
select 
    c.id,
    c.document_id,
    c.chunk_index,
    c.content,
    c.metadata,
    (
        coalesce(vec_weight / (rrf_k + v.rank_vec), 0.0) +
        coalesce(text_weight / (rrf_k + t.rank_text), 0.0)
    )::float as combined_score
from document_chunks c
left join vector_search v on c.id = v.id
left join text_search t on c.id = t.id
where v.id is not null or t.id is not null
order by combined_score desc
limit match_count;
$$;

-- 6. Habilitar Row Level Security (RLS) para conformidade de segurança
alter table documents enable row level security;
alter table document_chunks enable row level security;

-- Políticas de acesso permitindo operações do banco
create policy "Allow full access on documents" 
on documents for all using (true) with check (true);

create policy "Allow full access on document_chunks" 
on document_chunks for all using (true) with check (true);
