from pathlib import Path

import typer

import normasbr
from normasbr.classificacao.macrodimensao.existencia.classificador import (
    classificar_arquivo,
)
from normasbr.config import Config
from normasbr.ingestao import downloader
from normasbr.segmentacao import diff_segmentacao

app = typer.Typer(
    help=(
        "NormasBR: extração, segmentação e estruturação de normativas "
        "brasileiras.\n\nPipeline: ingerir > segmentar > estruturar > "
        "classificar."
    ),
    no_args_is_help=True,
)


def _mostrar_versao(valor: bool) -> None:
    if valor:
        typer.echo(f"normasbr {normasbr.__version__}")
        raise typer.Exit()


@app.callback()
def main(
    versao: bool = typer.Option(
        False,
        "--version",
        callback=_mostrar_versao,
        is_eager=True,
        help="Mostra a versão instalada e sai.",
    ),
) -> None:
    """Utilitário de linha de comando do normasbr."""


@app.command()
def ingerir(
    entrada: str = typer.Argument(help="URL ou caminho (arquivo/diretório) de origem."),
    saida: Path | None = typer.Option(
        None,
        "--saida",
        "-o",
        help="Diretório onde gravar os HTMLs normalizados. Sem ele, imprime na tela.",
    ),
) -> None:
    """Converte a entrada em HTML normalizado."""
    brutas = normasbr.despachar_ingestao(entrada, progresso=True)

    if saida is None:
        for bruta in brutas:
            typer.echo(bruta.texto)
        return

    saida.mkdir(parents=True, exist_ok=True)
    for i, bruta in enumerate(brutas, 1):
        nome = Path(bruta.origem).stem or f"normativa-{i}"
        _ = (saida / f"{nome}.html").write_text(bruta.texto, encoding="utf-8")
    typer.echo(f"{len(brutas)} arquivo(s) gravado(s) em {saida}")


@app.command()
def segmentar(
    entrada: str = typer.Argument(help="URL ou caminho (arquivo/diretório) de origem."),
) -> None:
    """Extrai blocos, segmenta e imprime cada segmento com seu tipo."""
    htmls = normasbr.despachar_ingestao(entrada, progresso=True)
    segmentador = normasbr.Segmentador()

    for html in htmls:
        blocos = normasbr.extrair_blocos(html)
        segmentos = segmentador.segmentar(blocos)
        print(f"Arquivo: {html.origem}")
        for s in segmentos:
            print(f"{s.tipo:22} | {s.texto}")


@app.command("diff_seg")
def diff_seg(
    snapshot: str = typer.Argument(help="Base de segmentação de referência."),
    novo: str = typer.Argument(help="Base de segmentação nova."),
    janela: int = typer.Option(0, help="Linhas de contexto exibidas ao redor do diff."),
) -> None:
    """Compara duas bases de segmentação e exibe as diferenças."""
    diff_segmentacao.exibir_comparacao(snapshot, novo, janela)


@app.command()
def estruturar(
    entrada: str = typer.Argument(help="URL ou caminho (arquivo/diretório) de origem."),
    saida: Path | None = typer.Option(
        None, "--saida", "-o", help="Arquivo YML de saída. Sem ele, imprime na tela."
    ),
) -> None:
    """Segmenta e estrutura a entrada, gerando normativas em YML."""
    normas = normasbr.processar(entrada, leniente=True, progresso=True)
    norma_yml = normasbr.formatar_normativas_yml(normas)

    if not saida:
        typer.echo(norma_yml)
    else:
        _ = saida.write_text(norma_yml, encoding="utf-8")


@app.command("classificar_macrodim")
def classificar_macrodim(
    entrada: Path = typer.Argument(help="Arquivo YML com as normativas."),
    saida: Path = typer.Argument(help="Arquivo CSV de saída."),
) -> None:
    """Classifica as macrodimensões (via LLM) das normativas de entrada."""
    _validar_config_llm()
    classificar_arquivo(entrada, saida)


@app.command("download")
def baixar(
    entrada: Path = typer.Argument(help="Arquivo TSV."),
    saida: Path = typer.Argument(help="Pasta de saída."),
) -> None:
    """Baixa os arquivos listados no TSV."""
    downloader.download_tsv(entrada, saida)


def _validar_config_llm() -> None:
    faltantes = [
        nome for nome in ("LLM_API_BASE", "LLM_MODEL") if not getattr(Config, nome)
    ]
    if faltantes:
        typer.echo(
            f"Defina {', '.join(faltantes)} no ambiente ou no .env para usar a "
            "classificação por LLM.",
            err=True,
        )
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
