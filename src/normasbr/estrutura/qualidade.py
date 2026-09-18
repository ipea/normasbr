from dataclasses import dataclass

from normasbr.estrutura.modelo import Normativa


@dataclass()
class AvaliacaoNormativa:
    pass


def avaliar_qualidade(norma: Normativa):
    """
    - Sequência de ids: existem gaps? Estão em ordem? Começa do 1?
    - Só existe um dispositivo efetivo com mesmo id?
    - Tem ementa? Tem preâmbulo?
    - Segue a hierarquia esperada dos tipos de dispositivos?
    - Como metrificar para usar como identificador norma em anexo?
    """
    pass
