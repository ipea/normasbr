"""API de alto nível: o pipeline completo em uma chamada."""

from pathlib import Path

from normasbr.estrutura.estruturador import estruturar
from normasbr.estrutura.modelo import Normativa
from normasbr.ingestao.despachante import despachar_ingestao
from normasbr.segmentacao.extrator_blocos import extrair_blocos
from normasbr.segmentacao.segmentador import Segmentador


def processar(
    entrada: str | Path,
    *,
    leniente: bool = True,
    progresso: bool = False,
) -> list[Normativa]:
    """Ingere, segmenta e estrutura uma normativa ou um diretório de normativas.

    Aceita URL, arquivo HTML/PDF/DOCX/TXT ou diretório. É o caminho recomendado
    para uso como biblioteca:

    >>> import normasbr
    >>> normas = normasbr.processar("lei.html")
    >>> normas[0].nome
    'LEI Nº 14.133, DE 1º DE ABRIL DE 2021'

    Args:
        entrada: URL ou caminho de arquivo/diretório.
        leniente: quando ``True``, segmentos que não puderem ser encaixados são
            ignorados; quando ``False``, levanta
            :class:`normasbr.erros.EstruturacaoInvalida`.
        progresso: exibe a barra de progresso da ingestão.

    Returns:
        Lista de :class:`~normasbr.estrutura.modelo.Normativa` não vazias.
    """
    segmentador = Segmentador()
    normas: list[Normativa] = []

    for bruta in despachar_ingestao(entrada, progresso=progresso):
        segmentos = segmentador.segmentar(extrair_blocos(bruta))
        normas += estruturar(segmentos, leniente=leniente)

    return normas
