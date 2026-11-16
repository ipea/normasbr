from pathlib import Path

import pytest

import normasbr
from normasbr.erros import EntradaInvalida, EstruturacaoInvalida
from normasbr.segmentacao.segmentador import (
    REGRAS_PADRAO,
    Segmentador,
    Segmento,
)

HTML_LEI = """<html><body>
<p>LEI Nº 1, DE 1º DE JANEIRO DE 2024</p>
<p>Dispõe sobre o pipeline de teste.</p>
<p>O PRESIDENTE DA REPÚBLICA Faço saber que o Congresso Nacional decreta e eu
sanciono a seguinte Lei:</p>
<p>Art. 1º Esta Lei testa o pipeline.</p>
</body></html>"""


def escrever_html(tmp_path: Path) -> Path:
    arquivo = tmp_path / "lei.html"
    arquivo.write_text(HTML_LEI, encoding="utf-8")
    return arquivo


def test_processar_aceita_str_e_path(tmp_path):
    arquivo = escrever_html(tmp_path)

    por_path = normasbr.processar(arquivo)
    por_str = normasbr.processar(str(arquivo))

    assert len(por_path) == len(por_str) == 1
    assert por_path[0].nome == "LEI Nº 1, DE 1º DE JANEIRO DE 2024"
    assert por_path[0].filhos[0].tipo == "artigo"  # pyright: ignore[reportAttributeAccessIssue]


def test_processar_leniente_ignora_documento_sem_estrutura(tmp_path):
    arquivo = tmp_path / "vazio.html"
    arquivo.write_text("<html><body><p>texto solto</p></body></html>", encoding="utf-8")

    assert normasbr.processar(arquivo, leniente=True) == []


def test_processar_estrito_levanta_erro_de_estruturacao():
    segmentos = [
        Segmento(tipo="TITULO_NORMATIVA", texto="LEI Nº 1", blocos=[]),
        Segmento(tipo="INICIO_BLOCO_ALTERACAO", texto='"', blocos=[]),
    ]

    with pytest.raises(EstruturacaoInvalida, match="segmento"):
        normasbr.estruturar(segmentos, leniente=False)

    assert normasbr.estruturar(segmentos, leniente=True) == []


def test_despachar_ingestao_aceita_path(tmp_path):
    arquivo = escrever_html(tmp_path)

    brutas = normasbr.despachar_ingestao(arquivo)

    assert len(brutas) == 1
    assert brutas[0].origem == str(arquivo)


def test_despachar_ingestao_arquivo_inexistente(tmp_path):
    with pytest.raises(EntradaInvalida, match="não encontrada"):
        normasbr.despachar_ingestao(tmp_path / "nao-existe.pdf")


def test_despachar_ingestao_extensao_invalida(tmp_path):
    arquivo = tmp_path / "lei.xyz"
    arquivo.write_text("conteudo", encoding="utf-8")

    with pytest.raises(EntradaInvalida, match="Formato não suportado"):
        normasbr.despachar_ingestao(arquivo)


def test_despachar_diretorio_avisa_sobre_arquivos_ignorados(tmp_path):
    escrever_html(tmp_path)
    (tmp_path / "ignorado.xyz").write_text("conteudo", encoding="utf-8")

    with pytest.warns(UserWarning, match="ignorado"):
        resultado = normasbr.despachar_ingestao(tmp_path)

    assert len(resultado) == 1


def test_segmentador_nao_compartilha_listas_globais():
    segmentador = Segmentador()
    segmentador.regras.clear()

    assert segmentador.regras is not REGRAS_PADRAO
    assert len(Segmentador().regras) == len(REGRAS_PADRAO)
