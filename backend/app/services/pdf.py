import asyncio
import logging
from dataclasses import dataclass
from typing import Union

import pymupdf as fitz

logger = logging.getLogger("docupulse.pdf")

# Limiar mínimo de caracteres para considerar uma página como "com texto".
# Abaixo disso, a página é tratada como imagem e enviada ao Gemini Vision.
TEXT_THRESHOLD = 50

# Resolução de renderização para OCR (DPI). 150 é suficiente para OCR de qualidade.
OCR_DPI = 150


@dataclass
class PDFPageResult:
    page_number: int
    text: str
    is_scanned: bool


class PDFExtractionService:
    """
    Serviço de extração inteligente de PDFs com PyMuPDF.

    Pipeline:
      1. Abre o PDF em memória (sem gravar em disco).
      2. Para cada página, tenta extrair texto digital.
      3. Se a página tem pouco texto (< TEXT_THRESHOLD chars), ela é
         considerada escaneada: renderiza como PNG e envia ao Gemini Vision.
      4. Concatena todo o conteúdo em Markdown estruturado.
    """

    async def extract_from_bytes(
        self,
        pdf_bytes: bytes,
        filename: str = "document.pdf",
        vision_service: Union["GeminiVisionService", None] = None,  # type: ignore[name-defined]
    ) -> str:
        """
        Extrai texto de um PDF em bytes.
        Retorna o conteúdo completo como texto/Markdown de forma assíncrona.
        """
        doc: fitz.Document = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_pages = doc.page_count
        logger.info("Iniciando extração de PDF '%s' (%d páginas).", filename, total_pages)

        page_results: list[PDFPageResult] = []

        for page_index in range(total_pages):
            page: fitz.Page = doc[page_index]
            page_number = page_index + 1

            # Tentativa 1: extração de texto digital
            raw_text: str = page.get_text("text").strip()

            if len(raw_text) >= TEXT_THRESHOLD:
                # Página com texto digital — usa diretamente
                page_results.append(
                    PDFPageResult(
                        page_number=page_number,
                        text=raw_text,
                        is_scanned=False,
                    )
                )
            else:
                # Página sem texto suficiente — renderiza como imagem para OCR
                if vision_service is not None and vision_service.is_configured:
                    try:
                        png_bytes = self._render_page_as_png(page)
                        ocr_text = await vision_service.extract_text_from_image(
                            image_bytes=png_bytes,
                            mime_type="image/png",
                        )
                        page_results.append(
                            PDFPageResult(
                                page_number=page_number,
                                text=ocr_text,
                                is_scanned=True,
                            )
                        )
                        logger.info("Página %d/%d: OCR via Gemini Vision aplicado.", page_number, total_pages)
                    except Exception as exc:
                        logger.warning("Falha no OCR da página %d: %s. Usando texto parcial.", page_number, exc)
                        page_results.append(
                            PDFPageResult(
                                page_number=page_number,
                                text=raw_text or f"[Página {page_number}: conteúdo visual não extraído]",
                                is_scanned=True,
                            )
                        )
                else:
                    # Sem Gemini Vision disponível, mantém o texto parcial
                    page_results.append(
                        PDFPageResult(
                            page_number=page_number,
                            text=raw_text or f"[Página {page_number}: sem texto detectado]",
                            is_scanned=False,
                        )
                    )

        doc.close()

        # Monta o documento final em Markdown estruturado
        return self._build_markdown(filename, page_results)

    def _render_page_as_png(self, page: "fitz.Page") -> bytes:  # type: ignore[name-defined]
        """Renderiza uma página do PDF como PNG bytes em resolução OCR."""
        mat = fitz.Matrix(OCR_DPI / 72, OCR_DPI / 72)  # 72 DPI é o padrão do PDF
        pixmap: fitz.Pixmap = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        return pixmap.tobytes("png")

    def _build_markdown(self, filename: str, pages: list[PDFPageResult]) -> str:
        """Concatena as páginas extraídas em um único documento Markdown."""
        total = len(pages)
        scanned_count = sum(1 for p in pages if p.is_scanned)
        digital_count = total - scanned_count

        header = (
            f"# Documento: {filename}\n"
            f"**Total de páginas:** {total}  \n"
            f"**Páginas digitais:** {digital_count}  \n"
            f"**Páginas escaneadas (OCR Gemini):** {scanned_count}\n\n"
            "---\n\n"
        )

        body_parts: list[str] = []
        for p in pages:
            badge = " _(OCR)_" if p.is_scanned else ""
            section = f"## Página {p.page_number}{badge}\n\n{p.text}\n"
            body_parts.append(section)

        return header + "\n".join(body_parts)


pdf_service = PDFExtractionService()
