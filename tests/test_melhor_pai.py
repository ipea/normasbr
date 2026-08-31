from normasbr.estrutura.modelo import (
    AlteracaoAgrupador,
    AlteracaoDispositivo,
    BlocoAlteracao,
    ContextoAlteracaoAgrupador,
    ContextoAlteracaoDispositivo,
    ElementoIntermediario,
    Normativa,
    Agrupador,
    Dispositivo,
)
from normasbr.estrutura.estruturador import melhor_pai


def assert_fora_blocos_alteracao(stack: list[ElementoIntermediario]):
    assert melhor_pai(ContextoAlteracaoAgrupador(), stack) is None
    assert melhor_pai(ContextoAlteracaoDispositivo(), stack) is None
    assert melhor_pai(AlteracaoAgrupador(), stack) is None
    assert melhor_pai(AlteracaoDispositivo(), stack) is None


def test_melhor_pai_caso_agrupadores():
    stack: list[ElementoIntermediario] = [
        Normativa(),  # 0
        Agrupador(tipo="livro"),  # 1
        Agrupador(tipo="capitulo"),  # 2
        Dispositivo(tipo="artigo"),  # 3
        Dispositivo(tipo="paragrafo"),  # 4
    ]

    assert melhor_pai(Dispositivo(tipo="inciso"), stack) == 4
    assert melhor_pai(Dispositivo(tipo="paragrafo"), stack) == 3

    assert melhor_pai(Dispositivo(tipo="artigo"), stack) == 2
    assert melhor_pai(Agrupador(tipo="sessao"), stack) == 2
    assert melhor_pai(Agrupador(tipo="capitulo"), stack) == 1
    assert melhor_pai(Agrupador(tipo="livro"), stack) == 0

    # Geralmente o bloco de alteração fica em artigos mas não teria problema aparecer aqui
    assert melhor_pai(BlocoAlteracao(), stack) == 4
    assert_fora_blocos_alteracao(stack)


def test_melhor_pai_caso_simples():
    stack: list[ElementoIntermediario] = [
        Normativa(),  # 0
    ]

    # Casos fáceis
    assert melhor_pai(Dispositivo(tipo="artigo"), stack) == 0
    assert melhor_pai(Agrupador(tipo="livro"), stack) == 0

    # Por mais que seja errado, ele deveria encaixar direto na normativa
    assert melhor_pai(Dispositivo(tipo="inciso"), stack) == 0

    # Normativa não aceita Bloco de Alteração nem seus filhos
    assert melhor_pai(BlocoAlteracao(), stack) is None
    assert_fora_blocos_alteracao(stack)


# Esse caso acontece na prática...
def test_melhor_pai_caso_artigo_inciso():
    stack: list[ElementoIntermediario] = [
        Normativa(),  # 0
        Dispositivo(tipo="artigo"),  # 1
        Dispositivo(tipo="inciso"),  # 2
    ]

    # Casos básicos
    assert melhor_pai(Dispositivo(tipo="artigo"), stack) == 0
    assert melhor_pai(Dispositivo(tipo="inciso"), stack) == 1
    assert melhor_pai(Dispositivo(tipo="alinea"), stack) == 2

    # Caso Agrupador, vai para a normativa
    assert melhor_pai(Agrupador(tipo="livro"), stack) == 0

    # Parágrafo vai para o artigo
    assert melhor_pai(Dispositivo(tipo="paragrafo"), stack) == 1

    # É esquisito, mas o bloco de alteração poderia ir pro inciso
    assert melhor_pai(BlocoAlteracao(), stack) == 2
    assert_fora_blocos_alteracao(stack)
