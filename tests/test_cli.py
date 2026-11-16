from pathlib import Path

from typer.testing import CliRunner

from normasbr.cli import app

runner = CliRunner()

HTML = "<html><body><p>Art. 1º Conteúdo de teste.</p></body></html>"


def criar_html(tmp_path: Path) -> Path:
    arquivo = tmp_path / "lei.html"
    arquivo.write_text(HTML, encoding="utf-8")
    return arquivo


def test_ingerir_imprime_html_sem_repr(tmp_path):
    arquivo = criar_html(tmp_path)

    resultado = runner.invoke(app, ["ingerir", str(arquivo)])

    assert resultado.exit_code == 0
    assert "NormativaBruta(" not in resultado.output
    assert "<p>" in resultado.output


def test_ingerir_grava_html_em_diretorio(tmp_path):
    arquivo = criar_html(tmp_path)
    saida = tmp_path / "normalizados"

    resultado = runner.invoke(app, ["ingerir", str(arquivo), "-o", str(saida)])

    assert resultado.exit_code == 0
    assert (saida / "lei.html").read_text(encoding="utf-8") == HTML


def test_version():
    resultado = runner.invoke(app, ["--version"])

    assert resultado.exit_code == 0
    assert resultado.output.startswith("normasbr ")
