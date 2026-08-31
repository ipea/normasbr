from dataclasses import dataclass, field
from difflib import SequenceMatcher
from itertools import pairwise
from typing import Literal


@dataclass(frozen=True)
class Segmento:
    tipo: str
    texto: str


@dataclass()
class Segmentacao:
    arquivo: str
    segmentos: list[Segmento]


Operacao = Literal[
    "equal",
    "delete",
    "insert",
    "change_type",
    "change_text",
    "change_all",
]


@dataclass(frozen=True)
class DiffSegmentacao:
    operacao: Operacao
    segmento_a: Segmento | None
    segmento_b: Segmento | None


type Contextos = list[list[DiffSegmentacao]]


@dataclass(frozen=True)
class ComparacaoBases:
    somente_original: list[str] = field(default_factory=list)
    somente_nova: list[str] = field(default_factory=list)
    # arquivos com mudança (já com janela de contexto aplicada)
    contextos_por_arquivo: dict[str, Contextos] = field(default_factory=dict)


def carregar_base(caminho: str) -> dict[str, Segmentacao]:
    """Lê um arquivo de snapshot e devolve o mapeamento arquivo -> segmentação."""
    segmentos: dict[str, Segmentacao] = {}
    arquivo_atual: str | None = None
    with open(caminho, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            if line.startswith("Arquivo: "):
                arquivo_atual = line.removeprefix("Arquivo: ")
                segmentos[arquivo_atual] = Segmentacao(arquivo_atual, [])
                continue

            if arquivo_atual is None:
                raise ValueError("Arquivo mal formatado: segmento antes de cabeçalho")

            tipo_seg, seg = line.rsplit("|", 1)
            segmentos[arquivo_atual].segmentos.append(Segmento(tipo_seg.strip(), seg))
    return segmentos


def comparar_bases(
    original: dict[str, Segmentacao],
    nova: dict[str, Segmentacao],
    janela: int = 0,
) -> ComparacaoBases:
    """Retorna um objeto com o comparativo das bases."""

    arquivos_original, arquivos_nova = set(original), set(nova)

    contextos_por_arquivo: dict[str, Contextos] = {}
    for arquivo in arquivos_original & arquivos_nova:
        # Obtém as diferenças entre os arquivos
        diff = diff_segmentos(original[arquivo].segmentos, nova[arquivo].segmentos)

        # Pega o contexto ao redor dos pontos de mudança
        contextos = aplicar_janela(diff, janela)
        if contextos:
            contextos_por_arquivo[arquivo] = contextos

    return ComparacaoBases(
        somente_original=sorted(arquivos_original - arquivos_nova),
        somente_nova=sorted(arquivos_nova - arquivos_original),
        contextos_por_arquivo=contextos_por_arquivo,
    )


def diff_segmentos(
    seg_a: list[Segmento], seg_b: list[Segmento]
) -> list[DiffSegmentacao]:
    """Alinha duas sequências de segmentos e classifica cada operação."""
    matcher = SequenceMatcher(None, a=seg_a, b=seg_b, autojunk=False)

    diff: list[DiffSegmentacao] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for i, j in zip(range(i1, i2), range(j1, j2)):
                diff.append(DiffSegmentacao("equal", seg_a[i], seg_b[j]))
        elif tag == "replace":
            indices_em_comum = min(i2 - i1, j2 - j1)

            # Quando estou nos índices em comum, é sinal que algum texto foi substituído
            for k in range(indices_em_comum):
                diff.append(_classificar_troca(seg_a[i1 + k], seg_b[j1 + k]))

            # Casos que só tem no segmento a, logo foram excluído.
            for k in range(indices_em_comum, i2 - i1):
                diff.append(DiffSegmentacao("delete", seg_a[i1 + k], None))

            # Casos que só tem no segmento b, logo foram inseridos.
            for k in range(indices_em_comum, j2 - j1):
                diff.append(DiffSegmentacao("insert", None, seg_b[j1 + k]))

        elif tag == "delete":
            for i in range(i1, i2):
                diff.append(DiffSegmentacao("delete", seg_a[i], None))
        elif tag == "insert":
            for j in range(j1, j2):
                diff.append(DiffSegmentacao("insert", None, seg_b[j]))
    return diff


def _classificar_troca(a: Segmento, b: Segmento) -> DiffSegmentacao:
    if a.tipo != b.tipo and a.texto == b.texto:
        return DiffSegmentacao("change_type", a, b)
    if a.tipo == b.tipo and a.texto != b.texto:
        return DiffSegmentacao("change_text", a, b)
    return DiffSegmentacao("change_all", a, b)


def aplicar_janela(diff: list[DiffSegmentacao], janela: int = 2) -> Contextos:
    if not diff:
        return []

    posicoes_modificadas = [i for i, d in enumerate(diff) if d.operacao != "equal"]
    if not posicoes_modificadas:
        return []

    # Pega os dados em que foram encontradas mudanças e mais a janela
    # ao redor das posições modificadas, mesmo que duplicando os valores.
    # Como uso um set + sorted, essas redundâncias são resolvidas.
    indices_exibir = sorted(
        {
            i
            for m in posicoes_modificadas
            for i in range(m - janela, m + janela + 1)
            if 0 <= i < len(diff)  # Remove casos "out of range"
        }
    )

    # Agrupa as janelas encontradas em blocos contíguos.
    # O pairwise transforma (1,2,3,4) em [(1,2), (2,3), (3, 4)].
    blocos: Contextos = []
    bloco: list[DiffSegmentacao] = [diff[indices_exibir[0]]]
    for prev, curr in pairwise(indices_exibir):
        # Quando os pares do pairwise são consecutivos,
        # adiciono o diff no bloco atual.
        if curr == prev + 1:
            bloco.append(diff[curr])
        # Quando não são consecutivos, fecho o bloco atual e crio um novo.
        else:
            blocos.append(bloco)
            bloco = [diff[curr]]
    blocos.append(bloco)
    return blocos


def formatar_contextos(contextos: Contextos) -> str:
    """Transforma uma lista de blocos de contexto em texto alinhado."""
    if not contextos:
        return ""

    textos: list[tuple[str, str]] = []
    for contexto in contextos:
        for diff in contexto:
            # Para cada operação diferente, crio a tupla que virará o texto final.
            match diff.operacao:
                case "equal":
                    assert diff.segmento_a is not None
                    textos.append((f"= {diff.segmento_a.tipo}", diff.segmento_a.texto))
                case "delete":
                    assert diff.segmento_a is not None
                    textos.append((f"- {diff.segmento_a.tipo}", diff.segmento_a.texto))
                case "insert":
                    assert diff.segmento_b is not None
                    textos.append((f"+ {diff.segmento_b.tipo}", diff.segmento_b.texto))
                case "change_type":
                    assert diff.segmento_a is not None and diff.segmento_b is not None
                    textos.append(
                        (
                            f"{diff.segmento_a.tipo} > {diff.segmento_b.tipo}",
                            diff.segmento_a.texto,
                        )
                    )
                case "change_text":
                    assert diff.segmento_a is not None and diff.segmento_b is not None
                    textos.append((f"{diff.segmento_a.tipo} -~", diff.segmento_a.texto))
                    textos.append((f"{diff.segmento_b.tipo} +~", diff.segmento_b.texto))
                case "change_all":
                    assert diff.segmento_a is not None and diff.segmento_b is not None
                    textos.append((f"< {diff.segmento_a.tipo}", diff.segmento_a.texto))
                    textos.append((f"> {diff.segmento_b.tipo}", diff.segmento_b.texto))
        textos.append(("", ""))

    if not textos:
        return ""

    # Calculo tamanho máximo do trecho inicial para formatar e facilitar a visualização,
    # adicionando espaços em branco a direita: notação "txt:<30".
    tam_max = max((len(operacao) for operacao, _ in textos), default=0)
    return "\n".join(
        f"{operacao:<{tam_max}} | {texto.strip()}" if operacao else ""
        for operacao, texto in textos
    )


def imprimir_comparacao(comparacao: ComparacaoBases) -> None:
    for arquivo in comparacao.somente_original:
        print(f"Arquivo {arquivo} só encontrado no original.")
    for arquivo in comparacao.somente_nova:
        print(f"Arquivo {arquivo} só encontrado no novo.")

    for arquivo, contextos in comparacao.contextos_por_arquivo.items():
        texto = formatar_contextos(contextos)
        if not texto:
            continue
        print(f"Arquivo: {arquivo.strip()}")
        print(texto)
        print()


def exibir_comparacao(snapshot_path: str, novo_path: str, janela: int) -> None:
    comparacao = comparar_bases(
        carregar_base(snapshot_path), carregar_base(novo_path), janela=janela
    )
    imprimir_comparacao(comparacao)
