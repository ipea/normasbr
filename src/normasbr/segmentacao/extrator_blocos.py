import re
from dataclasses import dataclass

from lxml import (
    etree,  # pyright: ignore[reportAttributeAccessIssue] -- extensão C, sem símbolo nos stubs
    html,
)

from normasbr.ingestao.normativa_bruta import NormativaBruta

BLOCK_TAGS = {"td", "p", "li", "blockquote", "h1", "h2", "h3", "h4"}

# Tags sem fechamento (void): não são empilhadas/alteradas pelo corretor.
TAGS_VAZIAS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}

# Tags de nível de bloco (estruturais). Um fechamento inline cujo elemento foi aberto
# ANTES do bloco mais interno é ilegal (quebra o bloco no parser).
TAGS_BLOCO = {
    "html",
    "body",
    "head",
    "p",
    "li",
    "td",
    "tr",
    "th",
    "ul",
    "ol",
    "table",
    "div",
    "blockquote",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "section",
    "article",
    "header",
    "footer",
    "nav",
    "main",
    "aside",
    "figure",
    "figcaption",
    "dl",
    "dt",
    "dd",
    "form",
    "select",
    "option",
}

# Algumas páginas (ex.: Emendas Constitucionais e Decretos gerados no Microsoft
# FrontPage) têm HTML malformado: um fechamento de tag inline (</font>) aparece no meio
# de um bloco abrindo um elemento que foi aberto antes do próprio bloco
# ("<p ...><span>...texto </font><a ...>..."). Isso faz o parser lxml fechar o <p> cedo
# e empurrar o conteúdo (links/continuações) para fora de qualquer tag de bloco; o texto
# então some do extrair_blocos e a normativa fica truncada.
#
# Corrige removendo fechamentos inline que não pertencem ao bloco corrente (cuja abertura
# está abaixo do bloco mais interno), preservando as tags estruturais de bloco (p, li, td,
# blockquote, h1-h4...) — inclusive um fechamento repetido como "</li></li>". Remover uma
# tag de fechamento não altera o texto visível nem a estrutura de blocos.
TAGS_INLINE_ORFAO_REMOVER = {
    "font",
    "span",
    "b",
    "strong",
    "i",
    "em",
    "u",
    "small",
    "big",
    "sub",
    "sup",
    "strike",
    "s",
    "del",
    "tt",
    "code",
    "q",
    "cite",
    "var",
    "nobr",
}

# Casa um comentário HTML ou uma tag (suporta atributos com ">" dentro de aspas).
_RE_TAG = re.compile(r"<!--.*?-->|<(?:[^<>\"']|\"[^\"]*\"|'[^']*')*>", re.DOTALL)
_RE_NOME_TAG = re.compile(r"</?\s*([a-zA-Z][a-zA-Z0-9]*)")


def _remover_fechamentos_orfaos(doc_html: str) -> str:
    """Remove fechamentos inline fora do bloco corrente, preservando o restante intacto."""
    pilha: list[str] = []
    partes: list[str] = []
    ultimo = 0

    for m in _RE_TAG.finditer(doc_html):
        parte = m.group(0)
        partes.append(doc_html[ultimo : m.start()])
        ultimo = m.end()

        # comentários/doctype/diretivas: mantém intactos
        if parte.startswith(("<!--", "<!", "<?")):
            partes.append(parte)
            continue

        nome_m = _RE_NOME_TAG.match(parte)
        if not nome_m:
            partes.append(parte)
            continue
        nome = nome_m.group(1).lower()
        eh_fechamento = parte.startswith("</")
        eh_autofechada = parte.rstrip().endswith("/>")

        if eh_fechamento:
            if nome in TAGS_VAZIAS or nome not in pilha:
                # Fechamento sem abertura na pilha: remove apenas se for tag inline
                # segura; preserva fechamento estrutural de bloco (auto-close <p>/<li>...).
                if nome in TAGS_INLINE_ORFAO_REMOVER:
                    continue
                partes.append(parte)
                continue

            # Posição da abertura mais recente de `nome` e do bloco mais interno aberto.
            topo = max(i for i, n in enumerate(pilha) if n == nome)
            blocos = [i for i, n in enumerate(pilha) if n in TAGS_BLOCO]
            bloco_topo = blocos[-1] if blocos else -1

            # Fechamento inline cuja abertura está abaixo do bloco mais interno:
            # quebraria o bloco no parser -> remove.
            if nome in TAGS_INLINE_ORFAO_REMOVER and topo < bloco_topo:
                continue

            # Fecha os elementos abertos dentro dele até o casamento.
            while pilha and pilha[-1] != nome:
                _ = pilha.pop()
            if pilha:
                _ = pilha.pop()
            partes.append(parte)
            continue

        if nome in TAGS_VAZIAS or eh_autofechada:
            partes.append(parte)
            continue
        pilha.append(nome)
        partes.append(parte)

    partes.append(doc_html[ultimo:])
    return "".join(partes)


def _corrigir_html_blocos(doc_html: str) -> str:
    return _remover_fechamentos_orfaos(doc_html)


@dataclass
class Bloco:
    texto: str
    links: list[tuple[str, str]]
    comeca_com_riscado: bool
    caminho: list[str]
    origem: str


def extrair_blocos(normativa_bruta: NormativaBruta) -> list[Bloco]:
    doc_html = _corrigir_html_blocos(normativa_bruta.texto)

    root = html.fromstring(doc_html)
    blocos = []

    for el in root.iter():
        if el.tag not in BLOCK_TAGS:
            continue

        texto = normalizar_texto(el)
        if not texto:
            continue

        # Quebra <\br> em vários blocos
        primeira_linha = True
        for linha in texto.split("\n"):
            if not linha:
                continue
            bloco = Bloco(
                texto=linha,
                links=[],
                comeca_com_riscado=comeca_com_riscado(el),
                caminho=extrair_caminho_tags(el),
                origem=normativa_bruta.origem,
            )
            # Links do elemento pertencem ao bloco como um todo; para evitar
            # duplicá-los em cada linha, atribuímos apenas ao primeiro.
            if primeira_linha:
                preencher_ancoras(el, bloco)
                primeira_linha = False
            blocos.append(bloco)

    return blocos


# ------------------------
# helpers
# ------------------------


def extrair_html_interno(el) -> str:
    return "".join(etree.tostring(child, encoding="unicode") for child in el)


def _extrair(node):
    """Coleta o texto *próprio* de um block tag.

    Descendentes que são eles mesmos block tags ( ``<p>``, ``<li>``,
    ``<blockquote>``, ``<h1>``-``<h4>`` ) são tratados como fronteira: não
    recursamos neles, pois viram blocos independentes em ``extrair_blocos``.
    Caso contrário, um ``<blockquote>`` ancestral acabaria incorporando o
    texto de todos os ``<p>`` internos, duplicando o conteúdo e fundindo
    caput + parágrafos + incisos num único bloco.

    O ``tail`` de um block tag filho (texto logo após seu fechamento)
    pertence ao ancestral, então é preservado.
    """
    partes = []
    if node.text:
        partes.append(node.text.replace("\n", " "))  # Removo \n quando não é tag <br>

    for child in node:
        if child.tag in BLOCK_TAGS:
            # Bloco filho vira bloco próprio: não incluir seu conteúdo,
            # mas o `tail` (eventual texto entre blocos filhos) é nosso.
            if child.tail:
                partes.append(child.tail.replace("\n", " "))
            continue

        partes.append(_extrair(child))

        if child.tag == "br":
            partes.append("\n")

        if child.tail:
            partes.append(
                child.tail.replace("\n", " ")
            )  # Removo \n quando não é tag <br>

    return "".join(partes)


def normalizar_texto(el) -> str:
    texto = _extrair(el)

    linhas = [linha.strip() for linha in texto.split("\n")]
    res = "\n".join(linha for linha in linhas if linha)

    txt = res.replace("\xa0", " ").replace("\t", " ")
    txt = re.sub(r"[ ]{2,}", " ", txt)
    txt = re.sub(r"\s+([,.;:!?])", r"\1", txt)
    return txt


def extrair_caminho_tags(el):
    return [ancestor.tag for ancestor in el.iterancestors()][::-1]


# ------------------------
# metadados
# ------------------------


def comeca_com_riscado(el) -> bool:
    for node in el.iter():
        # ignora o próprio elemento raiz
        if node is el:
            if node.text and node.text.strip():
                # texto direto no <p> → não é riscado
                return False
            continue

        # ignora anchors vazios tipo <a id="..."></a>
        if node.tag == "a" and not node.text_content().strip():
            continue

        # encontrou texto relevante
        texto = node.text_content().strip()
        if texto:
            return node.tag in {"s", "del", "strike"}

    return False


def preencher_ancoras(el, bloco: Bloco):
    for node in el.iter():
        if node.tag == "a":
            txt = node.text_content().replace("\xa0", " ").replace("\n", " ").strip()
            if txt and "href" in node.attrib:
                bloco.links.append((txt, node.attrib["href"]))
