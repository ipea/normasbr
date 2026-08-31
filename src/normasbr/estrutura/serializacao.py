from pathlib import Path
from typing import Any

import yaml

from normasbr.estrutura.modelo import Normativa


def carregar_normativas(caminho: Path) -> list[Normativa]:
    with open(caminho, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return [Normativa.model_validate(n) for n in data["normas"]]


ORDEM_PREFERENCIA_CAMPOS = [
    "classe",
    "tipo",
    "id",
    "nome",
    "origem",
    "efetivo",
    "ementa",
    "texto",
    "nome_penal",
    "nota_status",
    "preambulo",
    "links",
    "filhos",
]


def ordenar_dict(d):
    ordem_idx = {k: i for i, k in enumerate(ORDEM_PREFERENCIA_CAMPOS)}
    return dict(
        sorted(
            d.items(),
            key=lambda kv: ordem_idx.get(kv[0], len(ORDEM_PREFERENCIA_CAMPOS)),
        )
    )


def ordenar_recursivo(obj: Any) -> Any:
    if isinstance(obj, dict):
        obj = {
            k: ordenar_recursivo(v)
            for k, v in obj.items()
            # if v is not None and not (hasattr(v, "__len__") and len(v) == 0)
        }
        return ordenar_dict(obj)
    elif isinstance(obj, list):
        return [ordenar_recursivo(x) for x in obj]
    return obj


def gerar_dicionario_norma(normas: list[Normativa]):
    return {"normas": [ordenar_recursivo(n.model_dump()) for n in normas]}


def formatar_normativas_json(normas: list[Normativa]):
    import json

    return json.dumps(
        gerar_dicionario_norma(normas),
        sort_keys=False,
    )


def formatar_normativas_yml(normas: list[Normativa]):
    import yaml

    return yaml.safe_dump(
        gerar_dicionario_norma(normas),
        allow_unicode=True,
        sort_keys=False,
        width=200,
        indent=4,
    )
