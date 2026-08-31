import requests

from normasbr.ingestao.normativa_bruta import NormativaBruta


def extrair_html(url: str) -> NormativaBruta:
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:154.0) Gecko/20100101 Firefox/154.0"
    }
    r = requests.get(url, timeout=30, headers=headers)
    r.raise_for_status()

    encoding = r.encoding or r.apparent_encoding or "utf-8"
    if encoding.lower() in ("iso-8859-1", "latin-1"):
        encoding = "cp1252"

    texto = r.content.decode(encoding, errors="replace")

    return NormativaBruta(texto=texto, origem=url)
