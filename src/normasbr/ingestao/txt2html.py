from pathlib import Path

from normasbr.ingestao.normativa_bruta import NormativaBruta


def extrair_html(path: str) -> NormativaBruta:
    dados = Path(path).read_bytes()

    for enc in ("utf-8", "cp1252", "latin1"):
        try:
            texto_bruto = _converter(dados.decode(enc))
            return NormativaBruta(texto=texto_bruto, origem=path)
        except UnicodeDecodeError:
            pass

    return NormativaBruta(
        texto=_converter(dados.decode("utf-8", errors="replace")), origem=path
    )


def _converter(texto: str):
    body = [f"<p>{linha}</p>" for linha in texto.splitlines() if len(linha)]
    return f"<html><body>{'\n'.join(body)}</body></html>"
