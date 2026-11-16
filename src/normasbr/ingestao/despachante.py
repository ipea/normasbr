"""Despacho da ingestão: escolhe o conversor conforme a entrada."""

from __future__ import annotations

import warnings
from pathlib import Path

from tqdm import tqdm

from normasbr.erros import EntradaInvalida
from normasbr.ingestao import (
    doc2html,
    file2html,
    pdf2html,
    txt2html,
    url2html,
)
from normasbr.ingestao.normativa_bruta import NormativaBruta

EXTENSOES_SUPORTADAS = {".docx", ".txt", ".html", ".htm", ".pdf"}


def despachar_ingestao(
    entrada: str | Path,
    *,
    progresso: bool = False,
) -> list[NormativaBruta]:
    """Converte URL, arquivo ou diretório em normativas brutas (HTML canônico).

    Args:
        entrada: URL ``http(s)`` ou caminho de arquivo/diretório.
        progresso: exibe barra de progresso ao percorrer um diretório.

    Returns:
        Uma normativa bruta por arquivo processado.

    Raises:
        EntradaInvalida: caminho inexistente ou formato não suportado.
    """
    if isinstance(entrada, Path):
        entrada = str(entrada)

    if entrada.startswith(("http://", "https://")):
        return [url2html.extrair_html(entrada)]

    caminho = Path(entrada)
    if not caminho.exists():
        raise EntradaInvalida(f"Entrada não encontrada: {caminho}")

    if caminho.is_dir():
        return _ingerir_diretorio(caminho, progresso=progresso)

    bruta = extrair_arquivo(caminho)
    if not bruta:
        raise EntradaInvalida(
            f"Formato não suportado: {caminho.suffix or '(sem extensão)'} "
            f"({caminho}). Extensões aceitas: {_formatar_extensoes()}"
        )
    return [bruta]


def _ingerir_diretorio(caminho: Path, *, progresso: bool) -> list[NormativaBruta]:
    arquivos = sorted(p for p in caminho.iterdir() if p.is_file())
    iteravel = tqdm(arquivos, desc="Ingerindo arquivos") if progresso else arquivos

    result: list[NormativaBruta] = []
    ignorados: list[str] = []
    for p in iteravel:
        bruta = extrair_arquivo(p)
        if bruta:
            result.append(bruta)
        else:
            ignorados.append(p.name)

    if ignorados:
        warnings.warn(
            f"{len(ignorados)} arquivo(s) ignorado(s) em {caminho}: "
            f"{', '.join(sorted(ignorados))}. Extensões aceitas: {_formatar_extensoes()}",
            stacklevel=3,
        )

    return result


def _formatar_extensoes() -> str:
    return ", ".join(sorted(EXTENSOES_SUPORTADAS))


def extrair_arquivo(entrada: Path) -> NormativaBruta | None:
    """Converte um arquivo no formato do seu sufixo; ``None`` se não suportado."""
    if entrada.is_dir():
        return None

    match entrada.suffix.lower():
        case ".docx":
            return doc2html.extrair_html(str(entrada))
        case ".txt":
            return txt2html.extrair_html(str(entrada))
        case ".html" | ".htm":
            return file2html.extrair_html(str(entrada))
        case ".pdf":
            return pdf2html.extrair_html(str(entrada))
        case _:
            return None
