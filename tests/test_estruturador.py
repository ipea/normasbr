from normasbr.estrutura.estruturador import (
    criar_links,
    estruturar,
    obter_id_paragrafo,
    obter_tipo_agrupador,
)
from normasbr.estrutura.modelo import Agrupador, Dispositivo, Ementa, Normativa
from normasbr.segmentacao.extrator_blocos import Bloco
from normasbr.segmentacao.segmentador import Segmento, TipoSegmento


def seg(
    tipo: TipoSegmento,
    texto: str,
    riscado: bool = False,
    links: list[tuple[str, str]] | None = None,
) -> Segmento:
    bloco = Bloco(
        texto=texto,
        links=links or [],
        comeca_com_riscado=riscado,
        caminho=[],
        origem="lei.htm",
    )
    return Segmento(tipo=tipo, texto=texto, blocos=[bloco])


def test_criar_links():
    links = criar_links([("texto", "url"), ("outro", "url2")])

    assert [(link.texto, link.url) for link in links] == [
        ("texto", "url"),
        ("outro", "url2"),
    ]


def test_obter_tipo_agrupador():
    assert obter_tipo_agrupador("CAPÍTULO") == "capitulo"
    assert obter_tipo_agrupador("TÍTULO") == "titulo"
    assert obter_tipo_agrupador("SUB-SEÇÃO") == "subsecao"


def test_obter_tipo_agrupador_default():
    assert obter_tipo_agrupador("qualquer coisa") == "CAPITULO"


def test_obter_id_paragrafo():
    assert obter_id_paragrafo("§ 1º Texto do parágrafo.") == "1"
    assert obter_id_paragrafo("Parágrafo único. Texto.") == "unico"


def test_converter_titulo_gera_normativa_com_origem():
    normas = estruturar(
        [
            seg("TITULO_NORMATIVA", "LEI Nº 8.112"),
            seg("ARTIGO", "Art. 1º Fica aprovado o regime."),
        ]
    )

    assert len(normas) == 1
    assert isinstance(normas[0], Normativa)
    assert normas[0].nome == "LEI Nº 8.112"
    assert normas[0].origem == "lei.htm"


def test_estruturar_monta_hierarquia_completa():
    normas = estruturar(
        [
            seg("TITULO_NORMATIVA", "LEI Nº 8.112"),
            seg("EMENTA", "Dispoe sobre o regime juridico."),
            seg("AGRUPADOR", "CAPÍTULO I"),
            seg("ARTIGO", "Art. 1º Fica aprovado o regime."),
            seg("PARAGRAFO", "§ 1º Detalhamento do regime."),
        ]
    )

    assert len(normas) == 1
    norma = normas[0]
    assert len(norma.ementa) == 1 and isinstance(norma.ementa[0], Ementa)

    agrupadores = [f for f in norma.filhos if isinstance(f, Agrupador)]
    assert len(agrupadores) == 1
    assert agrupadores[0].tipo == "capitulo"

    artigos = [f for f in agrupadores[0].filhos if isinstance(f, Dispositivo)]
    assert len(artigos) == 1
    assert artigos[0].tipo == "artigo"
    assert artigos[0].id == "1"

    paragrafos = [f for f in artigos[0].filhos if isinstance(f, Dispositivo)]
    assert len(paragrafos) == 1
    assert paragrafos[0].tipo == "paragrafo"
    assert paragrafos[0].id == "1"


def test_normativa_sem_filhos_e_descartada():
    normas = estruturar([seg("TITULO_NORMATIVA", "LEI Nº 8.112")])

    assert normas == []


def test_estruturar_sem_titulo_nao_gera_normativa():
    normas = estruturar([seg("ARTIGO", "Art. 1º Órfão de título.")])

    assert normas == []


def test_segmento_riscado_gera_dispositivo_nao_efetivo():
    normas = estruturar(
        [
            seg("TITULO_NORMATIVA", "LEI Nº 8.112"),
            seg("ARTIGO", "Art. 1º Revogado.", riscado=True),
        ]
    )

    artigo = normas[0].filhos[0]
    assert isinstance(artigo, Dispositivo)
    assert artigo.efetivo is False


def test_ementa_com_links():
    normas = estruturar(
        [
            seg("TITULO_NORMATIVA", "LEI Nº 8.112"),
            seg("EMENTA", "Dispoe sobre normas.", links=[("fonte", "#origem")]),
            seg("ARTIGO", "Art. 1º Fica aprovado o regime."),
        ]
    )

    assert normas[0].ementa[0].links[0].url == "#origem"


def test_multiplas_normativas_em_sequencia():
    normas = estruturar(
        [
            seg("TITULO_NORMATIVA", "LEI Nº 1"),
            seg("ARTIGO", "Art. 1º Da primeira lei."),
            seg("TITULO_NORMATIVA", "LEI Nº 2"),
            seg("ARTIGO", "Art. 1º Da segunda lei."),
        ]
    )

    assert [n.nome for n in normas] == ["LEI Nº 1", "LEI Nº 2"]
