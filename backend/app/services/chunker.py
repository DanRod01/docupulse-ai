import re
from typing import List, Union
from app.schemas.document import ChunkItem, ChunkingConfig, MetadataValue


class RecursiveCharacterChunker:
    """Fatiador recursivo de texto inteligente para manter coesão semântica."""

    def __init__(
        self,
        separators: Union[List[str], None] = None,
        config: Union[ChunkingConfig, None] = None,
    ) -> None:
        self.separators: List[str] = separators or [
            "\n\n",  # Parágrafos
            "\n",  # Linhas
            ". ",  # Fim de frases
            "! ",
            "? ",
            "; ",
            " ",  # Palavras
            "",  # Caracteres
        ]
        self.config: ChunkingConfig = config or ChunkingConfig()

    def split_text(
        self,
        text: str,
        base_metadata: Union[dict[str, MetadataValue], None] = None,
    ) -> list[ChunkItem]:
        """Divide o texto em fragmentos respeitando o tamanho máximo e a sobreposição (overlap)."""
        cleaned_text = self._normalize_whitespace(text)
        if not cleaned_text:
            return []

        raw_chunks = self._split_recursive(
            text=cleaned_text,
            separators=self.separators,
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )

        chunk_items: list[ChunkItem] = []
        meta = base_metadata or {}

        for index, chunk_str in enumerate(raw_chunks):
            char_count = len(chunk_str)
            token_est = max(1, char_count // 4)
            chunk_items.append(
                ChunkItem(
                    chunk_index=index,
                    content=chunk_str,
                    character_count=char_count,
                    token_estimate=token_est,
                    metadata={**meta, "chunk_index": index},
                )
            )

        return chunk_items

    def _normalize_whitespace(self, text: str) -> str:
        """Remove espaços e quebras de linha excessivas sem alterar a semântica."""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _split_recursive(
        self,
        text: str,
        separators: List[str],
        chunk_size: int,
        chunk_overlap: int,
    ) -> List[str]:
        """Divide o texto de forma recursiva escolhendo o separador mais adequado."""
        if len(text) <= chunk_size:
            return [text] if text.strip() else []

        chosen_separator = ""
        new_separators = []

        for i, sep in enumerate(separators):
            if sep == "" or sep in text:
                chosen_separator = sep
                new_separators = separators[i + 1 :]
                break

        if chosen_separator:
            splits = text.split(chosen_separator)
        else:
            splits = list(text)

        # Recombina as partes respeitando o chunk_size e aplicando o overlap
        chunks: List[str] = []
        current_chunk: List[str] = []
        current_length = 0

        for segment in splits:
            if not segment:
                continue

            segment_len = len(segment) + (len(chosen_separator) if current_chunk else 0)

            # Se um único segmento for maior que o chunk_size e houver separadores mais finos
            if len(segment) > chunk_size and new_separators:
                # Esvazia o buffer atual antes de aprofundar
                if current_chunk:
                    chunk_text = chosen_separator.join(current_chunk).strip()
                    if chunk_text:
                        chunks.append(chunk_text)
                    current_chunk = []
                    current_length = 0

                sub_chunks = self._split_recursive(
                    text=segment,
                    separators=new_separators,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
                chunks.extend(sub_chunks)
                continue

            if current_length + segment_len <= chunk_size:
                current_chunk.append(segment)
                current_length += segment_len
            else:
                if current_chunk:
                    chunk_text = chosen_separator.join(current_chunk).strip()
                    if chunk_text:
                        chunks.append(chunk_text)

                # Aplica o overlap calculando os elementos anteriores a preservar
                overlap_buffer: List[str] = []
                overlap_len = 0
                for prev_seg in reversed(current_chunk):
                    if overlap_len + len(prev_seg) + len(chosen_separator) <= chunk_overlap:
                        overlap_buffer.insert(0, prev_seg)
                        overlap_len += len(prev_seg) + len(chosen_separator)
                    else:
                        break

                current_chunk = overlap_buffer + [segment]
                current_length = len(chosen_separator.join(current_chunk))

        if current_chunk:
            final_text = chosen_separator.join(current_chunk).strip()
            if final_text:
                chunks.append(final_text)

        return chunks


chunker_service = RecursiveCharacterChunker()
