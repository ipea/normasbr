import json

import yaml

from normasbr.estrutura.modelo import Dispositivo, Normativa
from normasbr.estrutura.serializacao import (
    carregar_normativas,
    formatar_normativas_json,
    formatar_normativas_yml,
    gerar_dicionario_norma,
    ordenar_dict,
    ordenar_recursivo,
)


def normas_exemplo() -> list[Normativa]:
    artigo = Dispositivo(
        classe="dispositivo",
        tipo="artigo",
        id="1",
        texto="Art. 1º Fica aprovado o regime.",
        efetivo=True,
    )
    return [Normativa(nome="LEI Nº 8.112", origem="lei.htm", filhos=[artigo])]


def test_ordenar_dict_segue_ordem_de_preferencia():
    ordenado = ordenar_dict(
        {"texto": "x", "filhos": [], "classe": "dispositivo", "zzz": 1}
    )

    chaves = list(ordenado.keys())
    assert chaves.index("classe") < chaves.index("texto") < chaves.index("filhos")
    assert chaves[-1] == "zzz"  # chave desconhecida vai para o final


def test_ordenar_recursivo_percorre_dict_e_listas():
    obj: dict[str, object] = {"b": [{"y": 1, "a": 2}], "a": {"z": 3, "m": 4}}
    ordenado = ordenar_recursivo(obj)

    assert isinstance(ordenado, dict)
    assert list(ordenado.keys()) == ["b", "a"]
    filhos = ordenado["a"]
    assert isinstance(filhos, dict)
    assert list(filhos.keys()) == ["z", "m"]


def test_ordenar_recursivo_retorna_escalares_intactos():
    assert ordenar_recursivo(42) == 42
    assert ordenar_recursivo("texto") == "texto"


def test_gerar_dicionario_norma_envolve_em_normas():
    dicio = gerar_dicionario_norma(normas_exemplo())

    assert set(dicio.keys()) == {"normas"}
    assert dicio["normas"][0]["nome"] == "LEI Nº 8.112"


def test_formatar_normativas_yml_roundtrip():
    yml = formatar_normativas_yml(normas_exemplo())
    dados = yaml.safe_load(yml)

    assert dados["normas"][0]["nome"] == "LEI Nº 8.112"
    assert dados["normas"][0]["filhos"][0]["tipo"] == "artigo"


def test_formatar_normativas_json_roundtrip():
    js = formatar_normativas_json(normas_exemplo())
    dados = json.loads(js)

    assert dados["normas"][0]["nome"] == "LEI Nº 8.112"


def test_carregar_normativas(tmp_path):
    yml = formatar_normativas_yml(normas_exemplo())
    arquivo = tmp_path / "normas.yml"
    arquivo.write_text(yml, encoding="utf-8")

    normas = carregar_normativas(arquivo)

    assert len(normas) == 1
    assert isinstance(normas[0], Normativa)
    assert normas[0].nome == "LEI Nº 8.112"
    assert normas[0].filhos[0].tipo == "artigo"  # pyright: ignore[reportAttributeAccessIssue]
