from pathlib import Path

from normasbr.ingestao import downloader
import typer
from tqdm import tqdm

import normasbr
from normasbr.classificacao.macrodimensao.existencia.anomalia import (
    classificar_anomalias,
)
from normasbr.classificacao.macrodimensao.existencia.classificador import (
    classificar_arquivo,
)
from normasbr.segmentacao import diff_segmentacao

app = typer.Typer(
    help=(
        "NormasBR: extração, segmentação e estruturação de normativas "
        "brasileiras.\n\nPipeline: ingerir > segmentar > estruturar > "
        "classificar."
    ),
    no_args_is_help=True,
)

# ingestao > extrator_bloco > segmentador > estruturador > classificador > visualizacao
# html     > ...            > ...         > yml          > parquet       > html/xlsx


@app.command()
def ingerir(
    entrada: str = typer.Argument(help="URL ou caminho (arquivo/diretório) de origem."),
) -> None:
    """Converte a entrada em HTML normalizado e imprime o conteúdo."""
    print(normasbr.despachar_ingestao(entrada))


@app.command()
def segmentar(
    entrada: str = typer.Argument(help="URL ou caminho (arquivo/diretório) de origem."),
) -> None:
    """Extrai blocos, segmenta e imprime cada segmento com seu tipo."""
    htmls = normasbr.despachar_ingestao(entrada)
    segmentador = normasbr.Segmentador()

    for html in tqdm(htmls, desc="Processando arquivos"):
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
    htmls = normasbr.despachar_ingestao(entrada)
    segmentador = normasbr.Segmentador()

    normas: list[normasbr.Normativa] = []
    for html in tqdm(htmls, desc="Processando arquivos"):
        blocos = normasbr.extrair_blocos(html)
        segmentos = segmentador.segmentar(blocos)
        normas += normasbr.estruturar(segmentos, leniente=True)

    norma_yml = normasbr.formatar_normativas_yml(normas)
    if not saida:
        print(norma_yml)
    else:
        with open(saida, mode="w") as f:
            _ = f.write(norma_yml)


@app.command("classificar_macrodim")
def classificar_macrodim(
    entrada: Path = typer.Argument(help="Arquivo YML com as normativas."),
    saida: Path = typer.Argument(help="Arquivo parquet de saída."),
) -> None:
    """Classifica as macrodimensões (via LLM) das normativas de entrada."""
    classificar_arquivo(entrada, saida)


@app.command("classificar_anomalias")
def classificar_anom(
    entrada: Path = typer.Argument(help="Arquivo YML com as normativas."),
) -> None:
    """Detecta anomalias estruturais (via LLM) nas normativas de entrada."""
    classificar_anomalias(entrada)


@app.command("download")
def dowload(
    entrada: Path = typer.Argument(help="Arquivo TSV."),
    saida: Path = typer.Argument(help="Pasta saida."),
) -> None:
    """Baixa arquivo tsv"""
    downloader.download_tsv(entrada, saida)


if __name__ == "__main__":
    app()
