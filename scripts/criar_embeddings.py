#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["model2vec"]
# ///

from collections import OrderedDict
from pathlib import Path

from model2vec import StaticModel

from normasbr.estrutura.serializacao import carregar_normativas
from normasbr.estrutura.travessia import (
    gerar_visualizacao_textual,
    procurar_dispositivos,
)


def carregar():
    normas = carregar_normativas(Path("./data/estrutura.yml"))
    artigos_brutos = procurar_dispositivos(normas, "artigo")
    resultado = {}
    for a in artigos_brutos:
        norma = a[0]

        if norma.nome not in resultado:
            ementa = norma.ementa[0].texto if len(norma.ementa) else None
            resultado[norma.nome] = {
                "nome": norma.nome,
                "ementa": ementa,
                "dispositivos": [],
            }

        # Gero o texto somente para a última posição da stack, o próprio dispositivo
        texto = gerar_visualizacao_textual(a[-1:])
        resultado[norma.nome]["dispositivos"].append(texto)
    return resultado


def criar_embeddings(normas):
    model = StaticModel.from_pretrained("minishlab/potion-multilingual-128M")
    cache = OrderedDict()

    for n in normas.values():
        ementa = n.get("ementa")
        if ementa and ementa not in cache:
            cache[ementa] = len(cache)
        for d in n["dispositivos"]:
            if d not in cache:
                cache[d] = len(cache)

    embeddings = model.encode(list(cache.keys()), show_progress_bar=True)
    return (cache, embeddings)


def main():
    import numpy as np
    import pickle

    normas = carregar()
    cache, embed = criar_embeddings(normas)

    np.save("data/embed.npy", embed)
    with open("data/embed_key.pkl", "wb") as f:
        pickle.dump(cache, f)
    with open("data/normas.pkl", "wb") as f:
        pickle.dump(normas, f)


main()
