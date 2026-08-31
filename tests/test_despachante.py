import pytest

from normasbr.ingestao import url2html
from normasbr.ingestao.despachante import despachar_ingestao, extrair_arquivo


def test_extrair_arquivo_html(tmp_path):
    arquivo = tmp_path / "lei.htm"
    arquivo.write_text("<html><body><p>Art. 1º</p></body></html>", encoding="utf-8")

    bruta = extrair_arquivo(arquivo)

    assert bruta is not None
    assert bruta.origem == str(arquivo)
    assert "Art. 1º" in bruta.texto


def test_extrair_arquivo_txt_envolve_em_paragrafos(tmp_path):
    arquivo = tmp_path / "lei.txt"
    arquivo.write_text("linha 1\n\nlinha 2", encoding="utf-8")

    bruta = extrair_arquivo(arquivo)

    assert bruta is not None
    assert "<p>linha 1</p>" in bruta.texto
    assert "<p>linha 2</p>" in bruta.texto


def test_extrair_arquivo_extensao_desconhecida_retorna_none(tmp_path):
    arquivo = tmp_path / "arquivo.xyz"
    arquivo.write_text("conteudo", encoding="utf-8")

    assert extrair_arquivo(arquivo) is None


def test_extrair_arquivo_diretorio_retorna_none(tmp_path):
    assert extrair_arquivo(tmp_path) is None


def test_despachar_diretorio_ignora_arquivos_invalidos(tmp_path):
    (tmp_path / "lei.htm").write_text("<p>Art. 1º</p>", encoding="utf-8")
    (tmp_path / "ignorado.xyz").write_text("conteudo", encoding="utf-8")

    resultado = despachar_ingestao(str(tmp_path))

    assert len(resultado) == 1
    assert resultado[0].origem.endswith("lei.htm")


def test_despachar_arquivo_invalido_levanta_excecao(tmp_path):
    arquivo = tmp_path / "arquivo.xyz"
    arquivo.write_text("conteudo", encoding="utf-8")

    with pytest.raises(Exception, match="Arquivo solicitado inválido"):
        despachar_ingestao(str(arquivo))


def test_despachar_url_delega_para_url2html(monkeypatch):
    def fake_extrair(url: str):
        from normasbr.ingestao.normativa_bruta import NormativaBruta

        return NormativaBruta(texto=f"<p>{url}</p>", origem=url)

    monkeypatch.setattr(url2html, "extrair_html", fake_extrair)

    resultado = despachar_ingestao("https://example.com/lei.htm")

    assert len(resultado) == 1
    assert resultado[0].origem == "https://example.com/lei.htm"
    assert "<p>https://example.com/lei.htm</p>" in resultado[0].texto
