import pymupdf

from normasbr.ingestao.normativa_bruta import NormativaBruta


def extrair_html(path: str) -> NormativaBruta:
    doc = pymupdf.open(path)
    html = ""
    for pagina in doc:
        valor_pagina = str(pagina.get_text("html"))
        html += valor_pagina

    return NormativaBruta(texto=html, origem=path)
