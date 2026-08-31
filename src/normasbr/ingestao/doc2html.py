import mammoth

from normasbr.ingestao.normativa_bruta import NormativaBruta


def convert_image(image):
    """No-op"""
    return {"src": ""}


def extrair_html(file_path_docx: str) -> NormativaBruta:
    with open(file_path_docx, "rb") as docx_file:
        result = mammoth.convert_to_html(
            docx_file, convert_image=mammoth.images.img_element(convert_image)
        )
    html = result.value
    return NormativaBruta(texto=str(html), origem=file_path_docx)
