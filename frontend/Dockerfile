# ==============================================================================
# DocuPulse AI - Frontend Dockerfile (Nuxt 4 / Nitro / Node.js 20)
# Multi-stage build otimizado para produção ultraleve
# ==============================================================================

# ── Estágio 1: Build da aplicação ─────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Instalação de dependências aproveitando cache de camadas
COPY package*.json ./
RUN npm ci

# Cópia do código-fonte
COPY . .

# Argumentos e variáveis de ambiente em tempo de build
ARG NUXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
ARG NUXT_PUBLIC_API_KEY=docupulse-dev-secret-2024
ENV NUXT_PUBLIC_API_BASE_URL=$NUXT_PUBLIC_API_BASE_URL \
    NUXT_PUBLIC_API_KEY=$NUXT_PUBLIC_API_KEY

# Build de produção do Nuxt 4 (gera a pasta .output)
RUN npm run build

# ── Estágio 2: Imagem final enxuta de execução ────────────────────────────────
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000 \
    HOST=0.0.0.0

# Copia apenas o bundle final gerado pelo Nitro no estágio 1
COPY --from=builder /app/.output ./.output

EXPOSE 3000

# Executa o servidor Nitro de alta performance
CMD ["node", ".output/server/index.mjs"]
