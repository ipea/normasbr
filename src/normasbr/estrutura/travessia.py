from collections.abc import Sequence

from normasbr.estrutura.modelo import (
    Agrupador,
    AlteracaoAgrupador,
    AlteracaoDispositivo,
    AlteracaoEmenta,
    BlocoAlteracao,
    ContextoAlteracaoAgrupador,
    ContextoAlteracaoDispositivo,
    Dispositivo,
    ElementoIntermediario,
    Elementos,
    Modificavel,
    Normativa,
)


def gerar_texto(elem: ElementoIntermediario | Elementos) -> list[str]:
    match elem:
        case Normativa(nome=nome, ementa=ementas):
            ementas = [e.texto for e in ementas if e.efetivo]
            ementa = [f"Ementa: {ementas[0]}" if len(ementas) else ""]
            return [f"Normativa: {nome}"] + ementa + [""]
        case Agrupador(id=id, texto=texto, tipo=tipo):
            return [f"{tipo} {id}{' - ' + texto if texto else ''}"] + [""]
        case Dispositivo(texto=texto):
            return [texto]
        case BlocoAlteracao():
            return ['"""']
        case ContextoAlteracaoDispositivo(id=id):
            return [f"{id}"] + ["......."]
        case ContextoAlteracaoAgrupador(id=id):
            return [f"{id}"] + ["......."]
        case AlteracaoDispositivo(id=id, texto=texto):
            return [f"{texto}"]
        case AlteracaoEmenta(texto=texto):
            return [texto]
        case AlteracaoAgrupador(id=id, texto=texto):
            return [f"{id}{' - ' + texto if texto else ''}"]
        case _:
            return [str(elem)]


def procurar_dispositivos(normas: list[Normativa], tipo_dispositivo: str):
    pendentes: list[list[Elementos]] = [
        [norma, f]
        for norma in normas
        for f in norma.filhos
        if getattr(f, "efetivo", False)
    ][::-1]

    while len(pendentes) > 0:
        pilha_atual = pendentes.pop(-1)

        elemento = pilha_atual[-1]
        if isinstance(elemento, Modificavel) and not elemento.efetivo:
            continue

        elif isinstance(elemento, Dispositivo):
            if elemento.tipo == tipo_dispositivo:
                yield pilha_atual

        elif isinstance(elemento, ElementoIntermediario):
            pendentes += [pilha_atual + [f] for f in elemento.filhos][::-1]


def gerar_visualizacao_textual(pilha: Sequence[ElementoIntermediario]) -> str:
    res = [linha for elem in pilha for linha in gerar_texto(elem)]

    pendentes = pilha[-1].filhos[::-1]
    while len(pendentes):
        f = pendentes.pop(-1)
        res += gerar_texto(f)
        if isinstance(f, ElementoIntermediario):
            pendentes += f.filhos[::-1]

    return "\n".join(res)
