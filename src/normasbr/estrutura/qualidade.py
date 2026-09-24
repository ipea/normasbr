from dataclasses import dataclass, field

from normasbr.estrutura.modelo import (
    Normativa,
)


@dataclass()
class AvaliacaoNormativa:
    achados: list[str] = field(default_factory=list)


def avaliar_qualidade(norma: Normativa):
    """
    - Sequência de ids: existem gaps? Estão em ordem? Começa do 1?
    - Só existe um dispositivo efetivo com mesmo id?
    - Tem ementa? Tem preâmbulo?
    - Segue a hierarquia esperada dos tipos de dispositivos?
    - Como metrificar para usar como identificador norma em anexo?
    """
    aval = AvaliacaoNormativa()

    if not len(norma.ementa):
        aval.achados.append("Normativa sem nenhuma ementa.")
    else:
        ementas_efetivas = numero_elementos_efetivos(norma.ementa)
        if ementas_efetivas == 0:
            aval.achados.append("Normativa sem nenhuma ementa efetiva.")
        if ementas_efetivas > 1:
            aval.achados.append(f"Normativa com {ementas_efetivas} ementas efetivas.")

    if not norma.preambulo:
        aval.achados.append("Normativa sem nenhum preâmbulo.")

    fila: list = [norma]
    while len(fila):
        atual = fila.pop(0)
        if not hasattr(atual, "filhos"):
            continue

        achados = list(avaliar_filhos(atual.filhos))
        aval.achados.extend(achados)
        fila.extend(atual.filhos)

    return aval


def numero_elementos_efetivos(elems: list) -> int:
    return sum(1 for i in elems if i.efetivo)


def tentar_converter_id():
    pass


def avaliar_filhos(elementos, path=""):
    unicos_efetivos: set[str] = set()

    for e in elementos:
        if not hasattr(e, "efetivo"):
            continue

        if not e.efetivo:
            continue
        if e.id in unicos_efetivos:
            yield f"O dispositivo '{path} > {e.tipo} {e.id}' aparece como efetivo mais de uma vez."
            continue

        unicos_efetivos.add(e.id)
