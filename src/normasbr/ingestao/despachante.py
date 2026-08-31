from pathlib import Path

from tqdm import tqdm

from normasbr.ingestao import (
    doc2html,
    file2html,
    pdf2html,
    txt2html,
    url2html,
)
from normasbr.ingestao.normativa_bruta import NormativaBruta


def despachar_ingestao(entrada: str) -> list[NormativaBruta]:
    if entrada.startswith(("http", "https")):
        return [url2html.extrair_html(entrada)]

    entrada_path = Path(entrada)
    if entrada_path.is_dir():
        res: list[NormativaBruta] = []
        for p in tqdm(entrada_path.iterdir(), desc="Ingerindo arquivos"):
            bruta = extrair_arquivo(p)
            if bruta:
                res.append(bruta)
        return res

    bruta = extrair_arquivo(entrada_path)
    if not bruta:
        raise Exception(f"Arquivo solicitado inválido: {entrada}")
    return [bruta]


def extrair_arquivo(entrada: Path) -> NormativaBruta | None:
    if entrada.is_dir():
        return None

    match entrada.suffix:
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
