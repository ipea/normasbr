from normasbr.estrutura.modelo import (
    Agrupador,
    BlocoAlteracao,
    Dispositivo,
    Ementa,
    Normativa,
)
from normasbr.estrutura.travessia import (
    gerar_texto,
    gerar_visualizacao_textual,
    procurar_dispositivos,
)


def normativa_com_artigos() -> Normativa:
    artigo = Dispositivo(
        classe="dispositivo",
        tipo="artigo",
        id="1",
        texto="Art. 1º Dispositivo efetivo.",
        efetivo=True,
    )
    revogado = Dispositivo(
        classe="dispositivo",
        tipo="artigo",
        id="2",
        texto="Art. 2º Revogado.",
        efetivo=False,
    )
    paragrafo = Dispositivo(
        classe="dispositivo",
        tipo="paragrafo",
        id="1",
        texto="§ 1º Detalhamento.",
        efetivo=True,
    )
    artigo.filhos = [paragrafo]
    agrupador = Agrupador(
        id="I", texto="Das disposições", tipo="capitulo", filhos=[artigo, revogado]
    )
    return Normativa(nome="LEI Nº 8.112", origem="lei.htm", filhos=[agrupador])


def test_gerar_texto_normativa_com_ementa():
    norma = Normativa(
        nome="LEI Nº 8.112",
        origem="",
        ementa=[Ementa(classe="ementa", texto="Dispoe sobre o regime.", efetivo=True)],
    )
    linhas = gerar_texto(norma)

    assert linhas[0] == "Normativa: LEI Nº 8.112"
    assert any(linha.startswith("Ementa: ") for linha in linhas)


def test_gerar_texto_normativa_sem_ementa():
    linhas = gerar_texto(Normativa(nome="LEI Nº 8.112", origem=""))

    assert linhas[0] == "Normativa: LEI Nº 8.112"


def test_gerar_texto_agrupador():
    agrupador = Agrupador(id="I", texto="Das disposições gerais", tipo="capitulo")
    linhas = gerar_texto(agrupador)

    assert linhas == ["capitulo I - Das disposições gerais", ""]


def test_gerar_texto_agrupador_sem_texto():
    agrupador = Agrupador(id="I", texto="", tipo="titulo")
    linhas = gerar_texto(agrupador)

    assert linhas == ["titulo I", ""]


def test_gerar_texto_dispositivo():
    dispositivo = Dispositivo(tipo="artigo", id="1", texto="Art. 1º Fica aprovado.")

    assert gerar_texto(dispositivo) == ["Art. 1º Fica aprovado."]


def test_gerar_texto_bloco_alteracao():
    assert gerar_texto(BlocoAlteracao()) == ['"""']


def test_gerar_texto_fallback():
    linhas = gerar_texto(Ementa(classe="ementa", texto="texto da ementa", efetivo=True))

    assert "texto da ementa" in linhas[0]


def test_procurar_dispositivos_encontra_apenas_o_tipo_pedido():
    norma = normativa_com_artigos()
    encontrados = list(procurar_dispositivos([norma], "artigo"))

    assert len(encontrados) == 1
    pilha = encontrados[0]
    assert isinstance(pilha[-1], Dispositivo)
    assert pilha[-1].tipo == "artigo"
    assert pilha[0] is norma
    assert isinstance(pilha[1], Agrupador)


def test_procurar_dispositivos_nao_desce_dentro_de_outro_dispositivo():
    # A travessia so percorre filhos de elementos intermediários genéricos
    # (Normativa, Agrupador...); dispositivos aninhados em outros dispositivos
    # (ex.: parágrafo dentro de artigo) não são alcançados.
    norma = normativa_com_artigos()

    assert list(procurar_dispositivos([norma], "paragrafo")) == []


def test_procurar_dispositivos_ignora_nao_efetivos():
    norma = normativa_com_artigos()
    encontrados = list(procurar_dispositivos([norma], "artigo"))

    assert len(encontrados) == 1
    dispositivo = encontrados[0][-1]
    assert isinstance(dispositivo, Dispositivo)
    assert dispositivo.texto == "Art. 1º Dispositivo efetivo."


def test_visualizacao_textual_percorre_hierarquia():
    norma = normativa_com_artigos()
    agrupador = norma.filhos[0]
    assert isinstance(agrupador, Agrupador)
    texto = gerar_visualizacao_textual([norma, agrupador])

    assert "Normativa: LEI Nº 8.112" in texto
    assert "capitulo I - Das disposições" in texto
    assert "Art. 1º Dispositivo efetivo." in texto
    assert "§ 1º Detalhamento." in texto


def test_visualizacao_textual_inclui_dispositivos_revogados():
    # Diferente de procurar_dispositivos, a visualização não filtra efetivo.
    norma = normativa_com_artigos()
    agrupador = norma.filhos[0]
    assert isinstance(agrupador, Agrupador)
    texto = gerar_visualizacao_textual([norma, agrupador])

    assert "Art. 2º Revogado." in texto
