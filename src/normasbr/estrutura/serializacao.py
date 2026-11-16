import json
from pathlib import Path
from typing import Any

import yaml

from normasbr.erros import EntradaInvalida
from normasbr.estrutura.modelo import Normativa


def carregar_normativas(caminho: str | Path) -> list[Normativa]:
    """Lê normativas estruturadas de um arquivo YAML ou JSON.

    Aceita tanto o objeto ``{"normas": [...]}`` gerado por
    :func:`formatar_normativas_yml`/:func:`formatar_normativas_json` quanto uma
    lista de normativas na raiz.

    Args:
        caminho: arquivo ``.yml``, ``.yaml`` ou ``.json``.

    Raises:
        EntradaInvalida: arquivo inexistente, extensão desconhecida ou conteúdo
            que não seja uma lista de normativas.
    """
    caminho = Path(caminho)
    if not caminho.exists():
        raise EntradaInvalida(f"Arquivo não encontrado: {caminho}")

    try:
        with open(caminho, "r", encoding="utf-8") as f:
            match caminho.suffix.lower():
                case ".json":
                    data = json.load(f)
                case ".yml" | ".yaml":
                    data = yaml.safe_load(f)
                case _:
                    raise EntradaInvalida(
                        f"Formato não suportado: {caminho.suffix or '(sem extensão)'} "
                        f"({caminho}). Use .yml, .yaml ou .json."
                    )
    except OSError as erro:
        raise EntradaInvalida(f"Não foi possível ler {caminho}: {erro}") from erro
    except (json.JSONDecodeError, yaml.YAMLError) as erro:
        raise EntradaInvalida(f"Conteúdo inválido em {caminho}: {erro}") from erro

    itens = data["normas"] if isinstance(data, dict) else data
    if not isinstance(itens, list):
        raise EntradaInvalida(
            f"Conteúdo inválido em {caminho}: esperava uma lista de normativas."
        )

    return [Normativa.model_validate(n) for n in itens]


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
    "notas_status",
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


def gerar_dicionario_norma(normas: list[Normativa]) -> dict[str, list[Any]]:
    """Converte as normativas no dicionário ``{"normas": [...]}`` ordenado."""
    return {"normas": [ordenar_recursivo(n.model_dump()) for n in normas]}


def formatar_normativas_json(normas: list[Normativa]):
    """Serializa as normativas como JSON indentado, com ``{"normas": [...]}``."""
    return json.dumps(
        gerar_dicionario_norma(normas),
        ensure_ascii=False,
        indent=2,
        sort_keys=False,
    )


def formatar_normativas_yml(normas: list[Normativa]):
    """Serializa as normativas como YAML com ``{"normas": [...]}``."""
    return yaml.safe_dump(
        gerar_dicionario_norma(normas),
        allow_unicode=True,
        sort_keys=False,
        width=200,
        indent=4,
    )
