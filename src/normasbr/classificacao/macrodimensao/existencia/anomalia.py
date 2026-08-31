from pathlib import Path

from pydantic import BaseModel

from normasbr.classificacao.estruturador_llm import EstruturadorDadosLLM
from normasbr.config import Config


class ExistenciaAnomalia(BaseModel):
    existe_anomalia: bool
    justificativa: str
    tags: list[str]


classificador = EstruturadorDadosLLM(
    template_prompt="""
        Este classificador tem por objetivo identificar se existe alguma anomalia estrutural no exemplo dado, considerando outros casos do mesmo dataset. Por anomalia, entenda um erro no processamento de dados que impediria classificações textuais futuras, que aqui deveriam ser dispositivos de normativas, com sua denominação, ementa, agrupadores (capitulo, parte ...) e o dispositivo legal em si, tipicamente artigos completos.

        Seja conservador ao apontar anomalias, erros de digitação não importam.
        Não considere como anomalia se ele está falando do artigo ou capítulo 10 sem mencionar do 1 ao 9, o importante é o trecho isolado.
        Ignore também a repetição do nome do agrupador, pois isso é só um artefato do pré processamento e não atrapalha classificações textuais. 
        Ignore dispositivos com numeração repetida, isso são dispositivos revogados que não foram removidos no no pré processamento.
        Ignore reticiências em casos de modificações de outros dispositivos. Isso é chamado omissis e é esperado quando não se deseja modificar outras coisas.

Dê uma justificativa sucinta também do motivo de ser uma anomalia.
Categorize as anomalias em tags sucintas para facilitar compreensão futura. Reutilize tags anteriores na medida do possível.

Não justifique textos sem anomalias.

    # Exemplos de outros textos:

    {exemplo}

    ------------

    # Tags existentes:

    {tags}

    # Normativa de interesse:

    {normativa}
    """,
    estrutura_esperada=ExistenciaAnomalia,
    modelo=Config.LLM_MODEL,
    url=Config.LLM_API_BASE,
)


def classificar_anomalias(
    banco: Path,
):
    import duckdb

    conn = duckdb.connect(banco)
    _ = conn.execute(
        """
        ALTER TABLE classificacao_macrodimensao ADD COLUMN IF NOT EXISTS anomalia bool;
        ALTER TABLE classificacao_macrodimensao ADD COLUMN IF NOT EXISTS justificativa_anomalia text;
        ALTER TABLE classificacao_macrodimensao ADD COLUMN IF NOT EXISTS tags_anomalia text;
        """
    )

    tags_db = conn.execute(
        "SELECT DISTINCT * FROM (SELECT regexp_split_to_table(tags_anomalia, '\\n') FROM classificacao_macrodimensao) "
    ).fetchall()
    tags_db = sorted([t[0] for t in tags_db if t[0] != ""])

    print(tags_db)

    tags: set[str] = set(tags_db)
    while True:
        prompts = conn.execute(
            """
            WITH res AS (
             SELECT prompt FROM classificacao_macrodimensao WHERE anomalia IS NULL
            )
            SELECT prompt FROM res USING SAMPLE 100;"""
        ).fetchall()

        if not len(prompts):
            break

        exemplos = conn.execute(
            """
            SELECT prompt FROM classificacao_macrodimensao USING SAMPLE 2;
            """
        ).fetchall()

        exemplo_final = f"""## Exemplo 1:
{exemplos[0][0]!s}

## Exemplo 2:
{exemplos[1][0]!s}
"""

        print("[NOVO LOTE]")
        print(exemplo_final)

        for p in prompts:
            prompt = str(p[0])  # pyright: ignore[reportAny]
            tags_txt = "\n".join(tags)

            classificacao = classificador(
                normativa=prompt, exemplo=exemplo_final, tags=tags_txt
            )

            tags = tags.union(classificacao.tags)

            print(f"""[Prompt]:
{prompt} 
[anomalia]: {classificacao.existe_anomalia}
[justificativa]: {classificacao.justificativa}
[tags]: {classificacao.tags}
""")
            _ = conn.execute(
                """ UPDATE classificacao_macrodimensao SET anomalia = ?, justificativa_anomalia = ?, tags_anomalia = ? WHERE prompt = ?; """,
                (
                    classificacao.existe_anomalia,
                    classificacao.justificativa,
                    "\n".join(classificacao.tags),
                    prompt,
                ),
            )
