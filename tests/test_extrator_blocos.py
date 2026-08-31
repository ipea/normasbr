from normasbr.ingestao.normativa_bruta import NormativaBruta
from normasbr.segmentacao.extrator_blocos import extrair_blocos


def bruta(html: str, origem: str = "teste.htm") -> NormativaBruta:
    return NormativaBruta(texto=html, origem=origem)


def test_um_bloco_por_tag_de_bloco():
    blocos = extrair_blocos(
        bruta("<html><body><p>Art. 1º</p><p>Parágrafo único.</p></body></html>")
    )

    assert len(blocos) == 2
    assert blocos[0].texto == "Art. 1º"
    assert blocos[1].texto == "Parágrafo único."


def test_ignora_blocos_vazios():
    blocos = extrair_blocos(bruta("<html><body><p>   </p><p>Texto</p></body></html>"))

    assert len(blocos) == 1
    assert blocos[0].texto == "Texto"


def test_br_quebra_em_varios_blocos():
    blocos = extrair_blocos(
        bruta("<html><body><p>linha um<br>linha dois<br>linha tres</p></body></html>")
    )

    assert [b.texto for b in blocos] == ["linha um", "linha dois", "linha tres"]


def test_normaliza_espacos_e_nbsp():
    blocos = extrair_blocos(
        bruta("<p>texto&nbsp;&nbsp; com&nbsp; espaços\t extras</p>")
    )

    assert blocos[0].texto == "texto com espaços extras"


def test_tags_de_bloco_filhas_nao_duplicam_texto_no_ancestral():
    html = "<blockquote><p>caput</p><p>inciso</p></blockquote>"
    blocos = extrair_blocos(bruta(html))

    assert [b.texto for b in blocos] == ["caput", "inciso"]


def test_links_capturados_no_primeiro_bloco():
    html = '<p><a href="#ancora">dispositivo</a> com link<br>segunda linha</p>'
    blocos = extrair_blocos(bruta(html))

    assert len(blocos) == 2
    assert blocos[0].links == [("dispositivo", "#ancora")]
    assert blocos[1].links == []


def test_ancora_sem_href_nao_gera_link():
    html = '<p><a id="x">âncora</a> texto</p>'
    blocos = extrair_blocos(bruta(html))

    assert blocos[0].links == []


def test_comeca_com_riscado():
    blocos = extrair_blocos(bruta("<p><s>Texto revogado.</s></p><p>Texto vigente.</p>"))

    assert blocos[0].comeca_com_riscado is True
    assert blocos[1].comeca_com_riscado is False


def test_anchor_vazio_nao_afeta_riscado():
    blocos = extrair_blocos(bruta('<p><a href="#x"></a>Texto vigente.</p>'))

    assert blocos[0].comeca_com_riscado is False


def test_fechamento_inline_orfao_nao_trunca_texto():
    html = '<p>texto </font><a href="#x">com link</a> e final</p>'
    blocos = extrair_blocos(bruta(html))

    assert len(blocos) == 1
    assert blocos[0].texto == "texto com link e final"


def test_origem_e_caminho_propagados():
    blocos = extrair_blocos(
        bruta("<html><body><div><p>texto</p></div></body></html>", origem="lei.htm")
    )

    assert blocos[0].origem == "lei.htm"
    assert blocos[0].caminho == ["html", "body", "div"]
