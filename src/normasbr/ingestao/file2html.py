from pathlib import Path

from normasbr.ingestao.normativa_bruta import NormativaBruta


def extrair_html(path: str) -> NormativaBruta:
    dados = Path(path).read_bytes()

    for enc in ("utf-8", "cp1252", "latin1"):
        try:
            return NormativaBruta(texto=dados.decode(enc), origem=path)
        except UnicodeDecodeError:
            pass

    return NormativaBruta(texto=dados.decode("utf-8", errors="replace"), origem=path)
