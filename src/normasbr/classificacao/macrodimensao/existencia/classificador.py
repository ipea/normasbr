import os
from pathlib import Path
from typing import cast

from pydantic import BaseModel
from tqdm import tqdm

from normasbr.classificacao.estruturador_llm import EstruturadorDadosLLM
from normasbr.config import Config
from normasbr.estrutura.modelo import ElementoIntermediario, Normativa
from normasbr.estrutura.serializacao import carregar_normativas
from normasbr.estrutura.travessia import (
    gerar_visualizacao_textual,
    procurar_dispositivos,
)


class ExistenciaMacrodimensoes(BaseModel):
    natureza_cooperacao: bool
    destinatario: bool
    setor: bool
    acesso: bool
    execucao: bool
    prestacao_contas: bool
    fundamentacao: str


classificador = EstruturadorDadosLLM(
    template_prompt="""
        Este classificador tem por objetivo examinar cada artigo de lei como unidade de análise independente e identificar a presença ou ausência das seguintes macrodimensões:

        - Acesso: O trecho determina como o ente subnacional se torna destinatário, quanto recebe ou como o recurso é entregue? Inclui elegibilidade, habilitação, proposta, pactuação, cálculo, rateio, valor, cronograma, liberação, repasse e transferência automática. Exclui a mera menção a "transferência" sem regra sobre destinação/recebimento.
        - Execução: O trecho determina como o recurso recebido deve ou pode ser aplicado, gerido, movimentado, acompanhado ou corrigido? Inclui finalidade, despesas, conta, movimentação, prazo, contratação, aplicação financeira, reprogramação, saldo, monitoramento e sanções de execução. Exclui descrição geral de política sem obrigação ou faculdade sobre o uso do recurso.
        - Prestação de Contas: O trecho determina como demonstrar, registrar, fiscalizar, analisar ou julgar o uso do recurso? Inclui comprovantes, relatórios, sistemas, prazos, análise, diligência, fiscalização, decisão, rejeição, responsabilização e restituição ligada às contas. Exclui uso de "controle" em sentido administrativo genérico, sem relação demonstrável com os recursos.

    Instruções de codificação:

    - Verificar, para cada artigo, a presença ou ausência de cada macrodimensão.
    - Seja sucinto na fundamentação.
    - Transcrever trechos do artigo que fundamentem a identificação, quando houver.
    - Indicar a localização precisa da evidência, mencionando artigo e, se necessário, inciso, parágrafo ou alínea.
    - Evitar inferências não sustentadas diretamente pelo texto legal.
    - Retorne um objeto json com os campos informados.

    Normativa de interesse:

    {normativa}
    """,
    estrutura_esperada=ExistenciaMacrodimensoes,
    # TODO: estruturar isso melhor
    modelo=Config.LLM_MODEL,
    url=Config.LLM_API_BASE,
    token_acesso=Config.LLM_API_KEY,
)


def classificar(normas: list[Normativa]):
    artigos = procurar_dispositivos(normas, "artigo")
    for a in artigos:
        # A pilha sempre termina num Dispositivo (intermediário), mas o tipo
        # declarado é Elementos (inclui terminais) e list é invariante.
        pilha = cast("list[ElementoIntermediario]", a)
        prompt = gerar_visualizacao_textual(pilha)
        classificacao = classificador(normativa=prompt)
        yield a, prompt, classificacao


def classificar_arquivo(
    entrada: Path,
    saida: Path,
):
    import duckdb

    normas = carregar_normativas(entrada)

    conn = duckdb.connect(saida)
    _ = conn.execute(
        """CREATE TABLE IF NOT EXISTS classificacao_macrodimensao (
            norma text,
            origem text,
            prompt text,
            modelo text,

            acesso bool,
            execucao bool,
            prestacao_contas bool,

            fundamentacao text,
            );
        """
    )

    artigos = list(procurar_dispositivos(normas, "artigo"))
    for a in tqdm(artigos):
        # A pilha sempre termina num Dispositivo (intermediário), mas o tipo
        # declarado é Elementos (inclui terminais) e list é invariante.
        pilha = cast("list[ElementoIntermediario]", a)
        norma = cast(Normativa, pilha[0])
        prompt = gerar_visualizacao_textual(pilha)
        modelo = (os.getenv("LLM_MODEL", ""),)

        print(f"[Normativa]\n{prompt}\n")
        existe = conn.execute(
            "select 1 from classificacao_macrodimensao where prompt = ? and modelo = ? limit 1",
            (prompt, modelo),
        ).fetchall()

        if len(existe):
            print("[Já Classificada]")
            continue

        classificacao = classificador(normativa=prompt)

        _ = conn.execute(
            """ INSERT INTO classificacao_macrodimensao VALUES (?,
            ?, ?, ?, ?, ?, ?, ?); """,
            (
                norma.nome,
                norma.origem,
                prompt,
                modelo,
                classificacao.acesso,
                classificacao.execucao,
                classificacao.prestacao_contas,
                classificacao.fundamentacao,
            ),
        )
        print(f"""
[Classificação]
acesso = {classificacao.acesso}
execucao = {classificacao.execucao}
prestacao_contas = {classificacao.prestacao_contas}
fundamentacao = {classificacao.fundamentacao}
""")

    # _ = conn.execute(
    #     f"COPY classificacao_macrodimensao TO '{saida!s}' (FORMAT parquet) "
    # )
