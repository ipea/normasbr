"""NormasBR: extração, segmentação e estruturação de normativas brasileiras.

Pipeline: ingestão (HTML/PDF/DOCX/TXT) > extração de blocos > segmentação >
estruturação > serialização (YML/JSON) > classificação.

Exemplo de uso da biblioteca:

    >>> import normasbr
    >>> normativas_brutas = normasbr.despachar_ingestao("lei.htm")
    >>> blocos = normasbr.extrair_blocos(normativas_brutas[0])
    >>> segmentos = normasbr.Segmentador().segmentar(blocos)
    >>> normas = normasbr.estruturar(segmentos, leniente=True)
"""

from importlib.metadata import PackageNotFoundError, version

from normasbr.estrutura.estruturador import estruturar
from normasbr.estrutura.modelo import (
    Agrupador,
    Dispositivo,
    Elemento,
    ElementoIntermediario,
    Elementos,
    Link,
    Normativa,
)
from normasbr.estrutura.serializacao import (
    carregar_normativas,
    formatar_normativas_json,
    formatar_normativas_yml,
)
from normasbr.estrutura.travessia import (
    gerar_texto,
    gerar_visualizacao_textual,
    procurar_dispositivos,
)
from normasbr.ingestao.despachante import despachar_ingestao
from normasbr.ingestao.normativa_bruta import NormativaBruta
from normasbr.segmentacao.extrator_blocos import Bloco, extrair_blocos
from normasbr.segmentacao.segmentador import (
    HEURISTICAS_PADRAO,
    REGRAS_PADRAO,
    Segmentador,
    Segmento,
)

try:
    __version__ = version("normasbr")
except PackageNotFoundError:  # executando a partir do código-fonte sem instalar
    __version__ = "0.0.0"

__all__ = [
    "HEURISTICAS_PADRAO",
    "REGRAS_PADRAO",
    "Agrupador",
    "Bloco",
    "Dispositivo",
    "Elemento",
    "ElementoIntermediario",
    "Elementos",
    "Link",
    "Normativa",
    "NormativaBruta",
    "Segmentador",
    "Segmento",
    "carregar_normativas",
    "despachar_ingestao",
    "estruturar",
    "extrair_blocos",
    "formatar_normativas_json",
    "formatar_normativas_yml",
    "gerar_texto",
    "gerar_visualizacao_textual",
    "procurar_dispositivos",
]
