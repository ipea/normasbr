from normasbr.segmentacao.extrator_blocos import Bloco
from normasbr.segmentacao.segmentador import (
    HEURISTICAS_PADRAO,
    REGRAS_PADRAO,
    Segmentador,
    Segmento,
    strip_accents,
)


def bloco(texto: str, origem: str = "teste.htm") -> Bloco:
    return Bloco(
        texto=texto, links=[], comeca_com_riscado=False, caminho=[], origem=origem
    )


def segmentar(texto: str) -> list[Segmento]:
    """Segmenta um texto único sem aplicar heurísticas (testa só as regras)."""
    return Segmentador(heuristicas=[]).segmentar([bloco(texto)])


def test_construtor_padrao_usa_regras_e_heuristicas_padrao():
    s = Segmentador()

    assert s.regras is REGRAS_PADRAO
    assert s.heuristicas is HEURISTICAS_PADRAO


def test_construtor_aceita_regras_e_heuristicas_customizadas():
    s = Segmentador(regras=[], heuristicas=[])

    assert s.regras == []
    assert s.heuristicas == []


def test_classifica_titulo_normativa():
    segs = segmentar("LEI Nº 8.112, DE 11 DE DEZEMBRO DE 1990")

    assert len(segs) == 1
    assert segs[0].tipo == "TITULO_NORMATIVA"


def test_classifica_artigo():
    segs = segmentar("Art. 1º Fica aprovada a Consolidação.")

    assert len(segs) == 1
    assert segs[0].tipo == "ARTIGO"


def test_texto_sem_regra_vira_desconhecido():
    segs = segmentar("qualquer coisa sem marcador")

    assert len(segs) == 1
    assert segs[0].tipo == "DESCONHECIDO"
    assert segs[0].incerto is False


def test_aspas_abrindo_gera_inicio_bloco_alteracao():
    segs = segmentar('"Art. 5º A redação fica assim:')

    assert segs[0].tipo == "INICIO_BLOCO_ALTERACAO"
    assert any(s.tipo == "ARTIGO" for s in segs)
    assert segs[-1].tipo != "FIM_BLOCO_ALTERACAO"


def test_aspas_fechando_gera_fim_bloco_alteracao():
    segs = segmentar('"Art. 5º A redação fica assim."(NR)')

    tipos = [s.tipo for s in segs]
    assert tipos[0] == "INICIO_BLOCO_ALTERACAO"
    assert tipos[-1] == "FIM_BLOCO_ALTERACAO"


def test_heuristicas_customizadas_sao_aplicadas():
    def duplica(segmentos: list[Segmento]) -> list[Segmento]:
        return segmentos + segmentos

    segs = Segmentador(regras=[], heuristicas=[duplica]).segmentar([bloco("x")])

    assert len(segs) == 2


def test_segmento_obter_links_e_origem():
    b = Bloco(
        texto="Art. 1º",
        links=[("link", "#destino")],
        comeca_com_riscado=False,
        caminho=[],
        origem="lei.htm",
    )
    seg = Segmento(tipo="ARTIGO", texto="Art. 1º", blocos=[b])

    assert seg.obter_links() == [("link", "#destino")]
    assert seg.obter_origem() == "lei.htm"


def test_segmento_is_riscado():
    b_riscado = Bloco(
        texto="t", links=[], comeca_com_riscado=True, caminho=[], origem="o"
    )
    b_livre = Bloco(
        texto="t", links=[], comeca_com_riscado=False, caminho=[], origem="o"
    )

    assert (
        Segmento(tipo="ARTIGO", texto="t", blocos=[b_riscado, b_riscado]).is_riscado()
        is True
    )
    assert (
        Segmento(tipo="ARTIGO", texto="t", blocos=[b_riscado, b_livre]).is_riscado()
        is False
    )
    assert Segmento(tipo="ARTIGO", texto="t", blocos=[]).is_riscado() is False


def test_pode_ter_continuacao():
    def seg_artigo(texto: str) -> Segmento:
        return Segmento(tipo="ARTIGO", texto=texto, blocos=[bloco(texto)])

    # Termina com pontuação → não continuável
    assert seg_artigo("Art. 1º Dispositivo completo.").pode_ter_continuacao() is False
    # Não termina com pontuação → continuável
    assert seg_artigo("Art. 1º Dispositivo sem ponto").pode_ter_continuacao() is True
    # Termina com abreviação → continuável
    assert seg_artigo("Art. 1º Nos termos do art.").pode_ter_continuacao() is True


def test_pode_ter_continuacao_depende_do_tipo():
    seg = Segmento(tipo="DESCONHECIDO", texto="sem ponto", blocos=[bloco("sem ponto")])

    assert seg.pode_ter_continuacao() is False


def test_strip_accents():
    assert strip_accents("Seção Artículo") == "Secao Articulo"
