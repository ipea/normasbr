#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["scikit-learn", "umap-learn", "numpy", "scipy"]
# ///

import pickle
import unicodedata

import numpy as np
from scipy import sparse


def carregar_textos_embedding():
    embed_bruto = np.load("data/embed.npy")
    with open("data/embed_key.pkl", "rb") as f:
        cache = pickle.load(f)
    with open("data/normas.pkl", "rb") as f:
        normas = pickle.load(f)

    n_dispositivos = sum(1 for n in normas.values() for _ in n["dispositivos"])
    embeddings = np.zeros((n_dispositivos, embed_bruto.shape[1]))

    texts = []
    i = 0
    for n in normas.values():
        ementa = n["ementa"]

        embed_ementa = None
        if ementa:
            embed_ementa = embed_bruto[cache[ementa], :]

        for d in n["dispositivos"]:
            id_cache = cache[d]
            emb = embed_bruto[id_cache, :]
            if embed_ementa is not None:
                emb = 0.8 * emb + 0.2 * embed_ementa

            embeddings[i, :] = emb
            texts.append(d)
            i += 1

    return texts, embeddings


class MiniBERTopic:
    def __init__(
        self,
        reducer=None,
        clusterer=None,
        vectorizer=None,
        bm25_weighting: bool = False,
        reduce_frequent_words: bool = False,
    ):
        self.reducer = reducer
        self.clusterer = clusterer
        self.vectorizer = vectorizer
        self.bm25_weighting = bm25_weighting
        self.reduce_frequent_words = reduce_frequent_words

        self.labels_ = None
        self.c_tf_idf_ = None
        self.topic_words_ = None

    def fit(self, texts, embeddings):
        texts = np.asarray(texts, dtype=object)
        embeddings = np.asarray(embeddings, dtype=np.float32)

        # Embeddings -> espaço reduzido
        if self.reducer is not None:
            embeddings = self.reducer.fit_transform(embeddings)

        # Espaço reduzido -> clusters
        self.labels_ = self.clusterer.fit_predict(embeddings)

        # Reordena os rótulos por tamanho do cluster: o maior vira 0,
        # o segundo maior vira 1, etc. Os outliers (-1) permanecem -1.
        self.labels_ = self._sort_labels_by_frequency(self.labels_)

        # Textos -> representação dos tópicos
        self._fit_ctfidf(texts)

        return self

    @staticmethod
    def _sort_labels_by_frequency(labels: np.ndarray) -> np.ndarray:
        unique, counts = np.unique(labels, return_counts=True)

        # Outliers (-1) não são reordenados.
        is_normal = unique != -1
        normal = unique[is_normal]
        normal_counts = counts[is_normal]

        # Ordem decrescente de tamanho.
        order = normal[np.argsort(normal_counts)[::-1]]
        remap = {int(old): new for new, old in enumerate(order)}

        return np.array(
            [remap.get(int(lbl), -1) for lbl in labels],
            dtype=labels.dtype,
        )

    def _fit_ctfidf(self, texts):
        topics = sorted(set(self.labels_) - {-1})

        # Cada tópico vira um único documento
        documents = [
            " ".join(text for text, label in zip(texts, self.labels_) if label == topic)
            for topic in topics
        ]

        # Bag of Words (contagens brutas)
        counts = self.vectorizer.fit_transform(documents).astype(np.float64)

        # ------------------------------------------------------------
        # c-TF-IDF
        #
        # BERTopic:
        #
        #   TF = frequência do termo no tópico
        #        / total de termos do tópico
        #
        #   IDF = log(1 + A / frequência_global)
        #
        #   A = média do número de termos por tópico
        #
        # Importante: df e A são calculados sobre as contagens brutas,
        # ANTES da normalização L1 (igual à implementação do BERTopic).
        # ------------------------------------------------------------

        # Número de termos em cada tópico (contagens brutas)
        topic_lengths = np.asarray(counts.sum(axis=1)).ravel()

        # Média inteira do número de termos por tópico
        A = int(topic_lengths.mean())

        # Frequência do termo em todos os tópicos (contagens brutas)
        df = np.asarray(counts.sum(axis=0)).ravel()

        # IDF
        if self.bm25_weighting:
            idf = np.log(1 + (A - df + 0.5) / np.maximum(df + 0.5, 1e-12))
        else:
            idf = np.log(1 + A / np.maximum(df, 1e-12))

        # Normalização L1 do TF.
        #
        # Fazemos manualmente para preservar a matriz esparsa.
        X = counts.multiply(
            1 / np.maximum(topic_lengths, 1)[:, None],
        ).tocsr()

        # reduce_frequent_words: raiz quadrada para diminuir o peso
        # de termos excessivamente frequentes (BERTopic).
        if self.reduce_frequent_words:
            X.data = np.sqrt(X.data)

        # Aplica IDF mantendo tudo esparso
        X = X @ sparse.diags(
            idf,
            offsets=0,
            format="csr",
        )

        self.c_tf_idf_ = X

        # ------------------------------------------------------------
        # Palavras mais representativas de cada tópico
        # ------------------------------------------------------------

        words = self.vectorizer.get_feature_names_out()

        self.topic_words_ = {}

        for row, topic in enumerate(topics):
            row_data = X.getrow(row)

            # Como a matriz é esparsa, não precisamos transformar
            # a linha inteira em array denso.
            order = np.argsort(row_data.data)[::-1]

            self.topic_words_[topic] = [
                (
                    words[index],
                    float(row_data.data[pos]),
                )
                for pos, index in zip(
                    order,
                    row_data.indices[order],
                )
            ]

    def get_topic(self, topic, n=10):
        return self.topic_words_[topic][:n]

    def get_topics(self, n=10):
        return {topic: words[:n] for topic, words in self.topic_words_.items()}


def strip_accents(s: str) -> str:
    return "".join(
        c
        for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn" and (c.isalpha() or c.isspace())
    )


stop = [
    "de",
    "a",
    "o",
    "que",
    "e",
    "do",
    "da",
    "em",
    "um",
    "para",
    "é",
    "com",
    "não",
    "uma",
    "os",
    "no",
    "se",
    "na",
    "por",
    "mais",
    "as",
    "dos",
    "como",
    "mas",
    "foi",
    "ao",
    "ele",
    "das",
    "tem",
    "à",
    "seu",
    "sua",
    "ou",
    "ser",
    "quando",
    "muito",
    "há",
    "nos",
    "já",
    "está",
    "eu",
    "também",
    "só",
    "pelo",
    "pela",
    "até",
    "isso",
    "ela",
    "entre",
    "era",
    "depois",
    "sem",
    "mesmo",
    "aos",
    "ter",
    "seus",
    "quem",
    "nas",
    "me",
    "esse",
    "eles",
    "estão",
    "você",
    "tinha",
    "foram",
    "essa",
    "num",
    "nem",
    "suas",
    "meu",
    "às",
    "minha",
    "têm",
    "numa",
    "pelos",
    "elas",
    "havia",
    "seja",
    "qual",
    "será",
    "nós",
    "tenho",
    "lhe",
    "deles",
    "essas",
    "esses",
    "pelas",
    "este",
    "fosse",
    "dele",
    "tu",
    "te",
    "vocês",
    "vos",
    "lhes",
    "meus",
    "minhas",
    "teu",
    "tua",
    "teus",
    "tuas",
    "nosso",
    "nossa",
    "nossos",
    "nossas",
    "dela",
    "delas",
    "esta",
    "estes",
    "estas",
    "aquele",
    "aquela",
    "aqueles",
    "aquelas",
    "isto",
    "aquilo",
    "estou",
    "está",
    "estamos",
    "estão",
    "estive",
    "esteve",
    "estivemos",
    "estiveram",
    "estava",
    "estávamos",
    "estavam",
    "estivera",
    "estivéramos",
    "esteja",
    "estejamos",
    "estejam",
    "estivesse",
    "estivéssemos",
    "estivessem",
    "estiver",
    "estivermos",
    "estiverem",
    "hei",
    "há",
    "havemos",
    "hão",
    "houve",
    "houvemos",
    "houveram",
    "houvera",
    "houvéramos",
    "haja",
    "hajamos",
    "hajam",
    "houvesse",
    "houvéssemos",
    "houvessem",
    "houver",
    "houvermos",
    "houverem",
    "houverei",
    "houverá",
    "houveremos",
    "houverão",
    "houveria",
    "houveríamos",
    "houveriam",
    "sou",
    "somos",
    "são",
    "era",
    "éramos",
    "eram",
    "fui",
    "foi",
    "fomos",
    "foram",
    "fora",
    "fôramos",
    "seja",
    "sejamos",
    "sejam",
    "fosse",
    "fôssemos",
    "fossem",
    "for",
    "formos",
    "forem",
    "serei",
    "será",
    "seremos",
    "serão",
    "seria",
    "seríamos",
    "seriam",
    "tenho",
    "tem",
    "temos",
    "tém",
    "tinha",
    "tínhamos",
    "tinham",
    "tive",
    "teve",
    "tivemos",
    "tiveram",
    "tivera",
    "tivéramos",
    "tenha",
    "tenhamos",
    "tenham",
    "tivesse",
    "tivéssemos",
    "tivessem",
    "tiver",
    "tivermos",
    "tiverem",
    "terei",
    "terá",
    "teremos",
    "terão",
    "teria",
    "teríamos",
    "teriam",
]


def main():

    from sklearn.cluster import HDBSCAN
    from sklearn.feature_extraction.text import CountVectorizer
    from umap import UMAP

    model = MiniBERTopic(
        reducer=UMAP(
            n_neighbors=15,
            n_components=5,
            min_dist=0.0,
            metric="cosine",
            random_state=42,
        ),
        clusterer=HDBSCAN(
            min_cluster_size=30,
            cluster_selection_method="eom",
        ),
        vectorizer=CountVectorizer(
            stop_words=[strip_accents(s) for s in stop],
            ngram_range=(1, 2),
            max_df=0.9,
            min_df=2,
        ),
        bm25_weighting=True,
        reduce_frequent_words=True,
    )

    (texts, embeddings) = carregar_textos_embedding()
    texts = [strip_accents(t) for t in texts]
    model.fit(texts, embeddings)

    for topic, words in model.get_topics(n=10).items():
        print(f"[Topico {topic}]")
        for w in words:
            print(f"  - {w[0]} - {w[1]:.2f}")


if __name__ == "__main__":
    main()
