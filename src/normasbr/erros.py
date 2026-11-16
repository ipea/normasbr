"""Erros públicos do normasbr.

Todos herdam de :class:`ErroNormasbr`, então um chamador pode capturar apenas a
base e tratar qualquer falha da biblioteca:

    try:
        normas = normasbr.processar("lei.pdf")
    except normasbr.ErroNormasbr as erro:
        print(erro)
"""


class ErroNormasbr(Exception):
    """Erro base da biblioteca."""


class EntradaInvalida(ErroNormasbr, ValueError):
    """Entrada inexistente, ilegível ou com formato não suportado."""


class EstruturacaoInvalida(ErroNormasbr):
    """Segmento que não pôde ser encaixado na árvore da normativa."""
