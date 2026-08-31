from __future__ import annotations

import itertools
import re
import unicodedata
from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from typing import Literal, Protocol, cast, override

from normasbr.segmentacao.extrator_blocos import (
    Bloco,
)

TipoSegmento = Literal[
    "DESCONHECIDO",
    "TITULO_NORMATIVA",
    "INICIO_BLOCO_ALTERACAO",
    "CONSIDERANDO",
    "ARTIGO",
    "PARAGRAFO",
    "INCISO",
    "ALINEA",
    "ITEM",
    "EMENTA",
    "CONTINUACAO",
    "ENUMERACAO",
    "FIM_BLOCO_ALTERACAO",
    "PREAMBULO",
    "CAMPO_VIDE",
    "AGRUPADOR",
    "DENOMINACAO_AGRUPADOR",
    "OMISSIS",
    "TITULO_AUTORIDADE",
    "INICIO_ANEXO",
    "DATA",
    "LIXO",
    "LOCAL_ORIGEM",
    "TEXTO_ANEXO",
    "NOME_AUTORIDADE",
    "NOME_PENAL",
    "PENA",
    "FUNDAMENTO_LEGAL",
]


@dataclass
class Segmento:
    tipo: TipoSegmento
    texto: str
    blocos: list[Bloco]
    incerto: bool = False

    @override
    def __str__(self) -> str:
        if self.tipo == "DESCONHECIDO":
            vermelho = "\033[31m"
            reset = "\033[0m"
            return f"{vermelho}[{self.tipo}] {self.texto}{reset}"

        return f"[{self.tipo!s}{'?' if self.incerto else ''}] {self.texto}"

    def obter_links(self) -> list[tuple[str, str]]:
        return [tup for b in self.blocos for tup in b.links]

    def is_riscado(self) -> bool:
        return len(self.blocos) > 0 and all(b.comeca_com_riscado for b in self.blocos)

    def obter_origem(self) -> str:
        return self.blocos[0].origem if self.blocos else ""

    def pode_ter_continuacao(self) -> bool:
        txt = self.texto.lower().strip()
        is_termina_com_pontuacao = txt.endswith((".", "!", "?", ":", ";"))
        is_termina_abreviacao = txt.endswith(("art.", "arts."))
        is_termina_com_pontovirgula_e = txt.endswith("; e")

        is_tipo_continuavel = self.tipo in {
            "ARTIGO",
            "PARAGRAFO",
            "INCISO",
            "ALINEA",
            "ITEM",
            "EMENTA",
            "PREAMBULO",
            "CONTINUACAO",
            "ENUMERACAO",
            "CONSIDERANDO",
            "DENOMINACAO_AGRUPADOR",
        }
        return (
            (not is_termina_com_pontuacao or is_termina_abreviacao)
            and not is_termina_com_pontovirgula_e
            and is_tipo_continuavel
        )


def strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


@dataclass()
class Regra:
    tipo: TipoSegmento
    pattern: re.Pattern[str]
    incerto: bool = False

    def match(self, txt: str) -> bool:
        return bool(self.pattern.match(txt))


class Matcher(Protocol):
    """Interface comum a todo elemento de padrão."""

    def match(
        self,
        segmentos: list[Segmento],
        idx: int,
        direcao: Literal[-1, 1],
    ) -> Iterator[int]: ...


# O que pode aparecer dentro de Sequencia/Alternativas
# ou nos campos anterior/posterior da heurística.
Elemento = Matcher | TipoSegmento | frozenset[TipoSegmento] | set[TipoSegmento]


@dataclass
class Repetir:
    """Casa uma sequência (variável) de segmentos cujo tipo esteja em `tipos`.

    tipos: str (um só) ou set/frozenset (qualquer um deles).
    min:   nº mínimo de ocorrências (default 1; 0 = opcional).
    max:   nº máximo, ou None para ilimitado.
    """

    tipos: TipoSegmento | set[TipoSegmento] | frozenset[TipoSegmento]
    min: int = 1
    max: int | None = None

    _tipos: frozenset[TipoSegmento] = field(init=False)

    def __post_init__(self) -> None:
        if isinstance(self.tipos, str):
            # isinstance(str) estreita para `str`, não para a união de
            # literais TipoSegmento; o valor é um TipoSegmento por construção.
            self._tipos = frozenset({self.tipos})
        else:
            self._tipos = frozenset(self.tipos)

    @staticmethod
    def de(x: Elemento) -> Matcher:
        """Normaliza um elemento cru num matcher.

        str / set / frozenset -> Repetir(min=1, max=1) ("exatamente um")
        Repetir/Sequencia/Alternativas -> devolve intacto
        """
        if isinstance(x, (Repetir, Sequencia, Alternativas)):
            return x
        if isinstance(x, (str, set, frozenset)):
            return Repetir(x, min=1, max=1)
        raise TypeError(f"Elemento de padrão inválido: {x!r}")

    def match(
        self,
        segmentos: list[Segmento],
        idx: int,
        direcao: Literal[-1, 1],
    ) -> Iterator[int]:
        conta, ponta = 0, idx
        while 0 <= ponta < len(segmentos) and segmentos[ponta].tipo in self._tipos:
            if self.max is not None and conta >= self.max:
                break
            conta += 1
            ponta += direcao
        # do mais guloso ao mínimo -> permite backtracking
        for n in range(conta, self.min - 1, -1):
            yield idx + n * direcao


class Sequencia:
    """Casa os elementos na ordem em que aparecem no documento.

    Com direcao +1 (posterior), o primeiro elemento é o mais próximo do alvo;
    com direcao -1 (anterior), a leitura é invertida: o último elemento é o
    mais próximo do alvo e o primeiro, o mais distante.
    """

    def __init__(self, *elementos: Elemento) -> None:
        self.elementos: list[Matcher] = [Repetir.de(e) for e in elementos]

    def match(
        self,
        segmentos: list[Segmento],
        idx: int,
        direcao: Literal[-1, 1],
    ) -> Iterator[int]:
        yield from self._em(segmentos, idx, direcao, 0)

    def _em(
        self,
        segmentos: list[Segmento],
        idx: int,
        direcao: Literal[-1, 1],
        pi: int,
    ) -> Iterator[int]:
        if pi == len(self.elementos):
            yield idx
            return
        # Em direcao -1 os elementos são percorridos em ordem reversa, para
        # que o último deles seja o mais próximo do alvo.
        p = pi if direcao == 1 else len(self.elementos) - 1 - pi
        for nxt in self.elementos[p].match(segmentos, idx, direcao):
            yield from self._em(segmentos, nxt, direcao, pi + 1)

    @override
    def __repr__(self) -> str:
        return f"Sequencia{self.elementos!r}"


class Alternativas:
    """Casa se QUALQUER um dos elementos casar (OR)."""

    def __init__(self, *elementos: Elemento) -> None:
        self.elementos: list[Matcher] = [Repetir.de(e) for e in elementos]

    def match(
        self,
        segmentos: list[Segmento],
        idx: int,
        direcao: Literal[-1, 1],
    ) -> Iterator[int]:
        for e in self.elementos:
            yield from e.match(segmentos, idx, direcao)

    @override
    def __repr__(self) -> str:
        return f"Alternativas{self.elementos!r}"


Padrao = Repetir | Sequencia | Alternativas


@dataclass
class HeuristicaPadraoSequencia:
    novo_tipo: TipoSegmento | Callable[[list[Segmento], int], TipoSegmento]
    tipo_alvo: TipoSegmento | Callable[[Segmento], bool]

    anterior: Elemento | None = None
    posterior: Elemento | None = None

    incerto: bool = False
    fn_aceitacao: Callable[[list[Segmento], int], bool] | None = None

    def _match_direcao(
        self,
        segmentos: list[Segmento],
        i: int,
        x: Elemento | None,
        direcao: Literal[-1, 1],
    ) -> bool:
        """direcao = -1 (anterior) ou +1 (posterior)."""
        if x is None:
            return True
        return (
            next(Repetir.de(x).match(segmentos, i + direcao, direcao), None) is not None
        )

    def _is_tipo_alvo(self, segmento: Segmento) -> bool:
        if callable(self.tipo_alvo):
            return self.tipo_alvo(segmento)
        return self.tipo_alvo == segmento.tipo

    def __call__(self, segmentos: list[Segmento]) -> list[Segmento]:
        res: list[Segmento] = segmentos[:]

        for i, seg in enumerate(res):
            if not self._is_tipo_alvo(seg):
                continue
            if not self._match_direcao(res, i, self.anterior, -1):
                continue
            if not self._match_direcao(res, i, self.posterior, +1):
                continue
            if self.fn_aceitacao and not self.fn_aceitacao(res, i):
                continue

            seg.tipo = (
                cast(TipoSegmento, self.novo_tipo)
                if isinstance(self.novo_tipo, str)
                else self.novo_tipo(segmentos, i)
            )
            if self.incerto:
                seg.incerto = True

        return res


def heuristica_ruidos(segmentos: list[Segmento]) -> list[Segmento]:
    contador = Counter(
        [s.texto for s in segmentos if len(s.texto) > 5 and s.tipo == "DESCONHECIDO"]
    )
    possiveis_ruidos = {txt for txt, contagem in contador.items() if contagem >= 5}
    if not len(possiveis_ruidos):
        return segmentos

    # Reclassifica casos que descobri que eram lixo
    for s in segmentos:
        if s.texto in possiveis_ruidos:
            s.tipo = "LIXO"
    return segmentos


def heuristica_dedup_titulo(segmentos: list[Segmento]) -> list[Segmento]:
    ultimo_titulo: str | None = None
    for s in segmentos:
        if s.tipo != "TITULO_NORMATIVA":
            continue

        if not ultimo_titulo or s.texto != ultimo_titulo:
            ultimo_titulo = s.texto
        else:
            # Se o ultimo titulo é igual ao ultimo identificado,
            # então é um cabeçalho do PDF, logo posso marcar como LIXO
            s.tipo = "LIXO"

    return segmentos


def heuristica_numero_paginas(segmentos: list[Segmento]) -> list[Segmento]:
    numeros = [int(s.texto) for s in segmentos if s.texto.isnumeric()]
    if len(numeros) < 3:
        return segmentos

    inc_1 = set()
    inc_2 = set()
    for a, b in itertools.pairwise(numeros):
        if a + 1 == b:
            inc_1.add(str(a))
        if a + 2 == b:
            inc_2.add(str(a))

    lista_paginas = None
    if len(inc_1) / len(numeros) > 0.6:
        lista_paginas = inc_1
    elif len(inc_2) / len(numeros) > 0.6:
        lista_paginas = inc_2

    if lista_paginas:
        for a in segmentos:
            if a.texto in lista_paginas:
                a.tipo = "LIXO"

    return segmentos


def heuristica_possivel_continuacao(segmentos: list[Segmento]) -> list[Segmento]:
    res = segmentos[:]

    for i in range(len(res) - 1):
        # Pega o ultimo elemento que não seja lixo
        prev = next(
            (res[i - j] for j in range(i + 1) if res[i - j].tipo != "LIXO"), None
        )

        if not prev:
            continue

        curr = res[i + 1]

        if curr.tipo != "DESCONHECIDO":
            continue

        curr_txt = curr.texto

        if not curr_txt:
            continue

        if prev.pode_ter_continuacao():
            curr.tipo = "CONTINUACAO"
            curr.incerto = True

    return res


def corrige_bloco_parentesis(segmentos: list[Segmento]) -> list[Segmento]:
    parentesis_aberto = False
    for i in range(1, len(segmentos) - 1):
        curr = segmentos[i]
        curr_txt = curr.texto.strip()

        # Descarto quando o anterior é Desconhecido ou Anexo
        if parentesis_aberto and segmentos[i - 1].tipo not in (
            "DESCONHECIDO",
            "TEXTO_ANEXO",
            "INICIO_ANEXO",
        ):
            curr.tipo = "CONTINUACAO"

        for c in curr_txt:
            if c == "(":
                parentesis_aberto = True

            if c == ")" and parentesis_aberto:
                parentesis_aberto = False

        # "Fechamentos" improvisados do parêntesis
        if curr_txt and curr_txt[-1] in {"}", ";"} and parentesis_aberto:
            parentesis_aberto = False

        # Situação comum: não fecham o parêntesis, mas é uma referência de outra normativa,
        # que tipicamente termina com um ano/data.
        if parentesis_aberto and re.search(
            r" de (\d{2}[/.-]\d{2}[/.-])?\d{4}$", curr_txt
        ):
            parentesis_aberto = False

        if (
            curr_txt.startswith("(")
            and curr.tipo == "DESCONHECIDO"
            and segmentos[i - 1].tipo != "DESCONHECIDO"
        ):
            curr.tipo = "CONTINUACAO"

    return segmentos


class Segmentador:
    def __init__(
        self,
        regras: list[Regra] | None = None,
        heuristicas: list[Callable[[list[Segmento]], list[Segmento]]] | None = None,
    ):
        self.regras: list[Regra] = regras if regras is not None else REGRAS_PADRAO
        self.heuristicas: list[Callable[[list[Segmento]], list[Segmento]]] = (
            heuristicas if heuristicas is not None else HEURISTICAS_PADRAO
        )

    def segmentar(self, blocos: Iterable[Bloco]) -> list[Segmento]:
        segs = [seg for bloco in blocos for seg in self._gerar_segmentos(bloco)]
        segs = self._refinar(segs)
        return segs

    def _gerar_segmentos(self, bloco: Bloco):
        txt_original = bloco.texto
        txt = strip_accents(txt_original.strip()).replace("\n", " ")

        # Aspas (duplas ou simples, retas ou tipograficas) delimitam bloco de
        # alteracao. O planalto usa os pares " " " (duplas) e ‘ ’ / ' (simples);
        # tratamos todos como limitadores, pois o importante e separar o marcador
        # do conteudo.
        if txt.startswith(('"', "“", "‘", "'")):
            aspas = txt[0]
            yield Segmento(texto=aspas, tipo="INICIO_BLOCO_ALTERACAO", blocos=[bloco])
            txt_original = txt_original[txt_original.find(aspas) + 1 :].strip()
            txt = txt[1:].strip()

        TERMINA_BLOCO = re.compile(r"[\"”’'] ?(\(NR\))?$")
        match_termino_bloco = next(TERMINA_BLOCO.finditer(txt), None)
        segmento_sufixo = None

        if match_termino_bloco:
            ini = match_termino_bloco.start()
            fim = match_termino_bloco.end()

            txt_original = TERMINA_BLOCO.sub("", txt_original)
            segmento_sufixo = Segmento(
                texto=txt[ini:fim],
                tipo="FIM_BLOCO_ALTERACAO",
                blocos=[bloco],
            )
            txt = txt[:ini].strip()

        regra_aceita = None
        for regra in self.regras:
            if regra.match(txt):
                regra_aceita = regra
                break

        if regra_aceita:
            yield Segmento(texto=txt_original, tipo=regra_aceita.tipo, blocos=[bloco])
        else:
            yield Segmento(texto=txt_original, tipo="DESCONHECIDO", blocos=[bloco])

        if segmento_sufixo:
            yield segmento_sufixo

    def _refinar(self, segmentos: list[Segmento]) -> list[Segmento]:
        for h in self.heuristicas:
            segmentos = h(segmentos)
        return segmentos


REGRAS_PADRAO = [
    Regra(
        "TITULO_NORMATIVA",
        re.compile(
            r"^(LEI|DECRETO|EMENDA CONSTITUCIONAL|CONSTITUICAO DA REPUBLICA|MEDIDA PROVISORIA|PORTARIA|RESOLUCAO|INSTRUCAO NORMATIVA)\b"
        ),
    ),
    Regra(
        "EMENTA",
        re.compile(
            r"(^Dispoe sobre|^Regulamenta|^Estabelece normas|e da outras providencias\.$|^Codigo Penal\.$)"
        ),
    ),
    Regra(
        "EMENTA",
        re.compile(
            r"^(Cria|Institui|Altera|Acrescenta|Estabelece|Aprova|Consolida|Regulamenta)\b"
        ),
        incerto=True,
    ),
    Regra(
        "CAMPO_VIDE",
        re.compile(
            r"^(Mensagem de veto|Vigencia( encerrada)?|Regulamento|Promulgacao( (das?|de) partes? vetadas?)?|Texto compilado|Conversao da (Medida Provisoria|MPv?).*|\(?Vide .*|\(?Promulgacao .* vetadas?\)?|Exposicao de motivos|Producao de efeito|Voto|( ?\(ADIN[^)]+\))+)$",
            re.IGNORECASE,
        ),
    ),
    Regra(
        "FUNDAMENTO_LEGAL",
        re.compile(
            r"^(Fundamentacao|Fundamento) Legal:",
            re.IGNORECASE,
        ),
    ),
    Regra(
        "AGRUPADOR",
        # Forço tamanho reduzido intencionalmente para não capturar coisas demais.
        re.compile(
            r"^(CAPITULO|LIVRO|PARTE|SECAO|SUB-?SECAO|TITULO)( .{,10})?$", re.IGNORECASE
        ),
    ),
    # Romano + tudo em maiúsculo
    Regra(
        "AGRUPADOR",
        re.compile(r"^[MDCLXVI]+ *[-–] *[A-Z, ]+$"),
    ),
    Regra(
        "DENOMINACAO_AGRUPADOR",
        re.compile(
            r"(Disposicoes Preliminares|Disposicoes Gerais|Disposicoes Finais|Disposicoes Transitorias)",
            re.IGNORECASE,
        ),
    ),
    Regra("CONSIDERANDO", re.compile(r"^(Considerando|CONSIDERANDO)\b")),
    Regra("ARTIGO", re.compile(r"^Art\.")),
    Regra("PARAGRAFO", re.compile(r"(^Paragrafo unico|^§)", re.IGNORECASE)),
    # Curiosamente, achei um caso de número romano de inciso que trocaram I -> l
    Regra("INCISO", re.compile(r"^[MDCLXVIl]+([-–][A-Z]{1,5})?\s?[-–]")),
    Regra("ALINEA", re.compile(r"^[a-z]{1,5}([-–][A-Z0-9]{1,5})?\)")),
    # Tem que ter o espaço em branco aqui senão ele considera que alguns números no início da linha (ex: 1.000)
    # são continuações itens
    Regra("ITEM", re.compile(r"^[0-9]{1,5}([-–][A-Z]{1,5})?\.\s")),
    Regra("PENA", re.compile(r"^Pena\b\s*[-–—:]", re.IGNORECASE)),
    Regra("OMISSIS", re.compile(r"^[.]{4,}$")),
    Regra(
        "TITULO_AUTORIDADE", re.compile(r"^Ministr. de Estado d[aoe] ", re.IGNORECASE)
    ),
    Regra(
        "INICIO_ANEXO",
        re.compile(
            r"^(ANEXO|A N E X O)(\s*[ÃÕÂÁÉÍÓÚÇÀ\sA-Z0-9,ºª/\-\–\—]+)?(\s*\([^\(\)]*\))*$",
        ),
    ),
    Regra(
        "DATA",
        re.compile(
            r"^[A-Z][\w .-]+,( em)? \d+(o|º|°)? de (janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro) de \d{4}",
            re.IGNORECASE,
        ),
    ),
    Regra(
        "LIXO",
        re.compile(
            r"^Este (texto|conteudo) nao substitui|^Publicado em|^Processo( de origem)? SEI.*|^\*$|.*Compartilhe.*(Facebook|Whatsapp|Linkedin|Instagram).*|^((Up|Down)|(Texto para impressao)|(Texto compilado Texto atualizado)|Download para anexo.*)$",
            re.IGNORECASE,
        ),
    ),
    Regra(
        "LIXO",
        re.compile(
            r"^\d+/\d+$",  # Número da página
            re.IGNORECASE,
        ),
    ),
    # Cabeçalho/rodapé/assinatura de páginas do DOU e SEI (extraídas de PDF),
    # que aparecem repetidas em cada página e não fazem parte da norma.
    Regra(
        "LIXO",
        re.compile(
            r"^(?:Imprensa Nacional|Sum[áa]rio|www\.in\.gov\.br|ouvidoria@in\.gov\.br)$"
            + r"|^REP[ÚU]BLICA FEDERATIVA DO BRASIL(?:.*IMPRENSA NACIONAL)?$"
            + r"|^ISSN \d{4}-\d{4}$"
            + r"|^Ano \w+ N[ºo] \d"
            + r"|^Documento assinado digitalmente conforme MP n[ºo] "
            + r"|^que institui a Infraestrutura de Chaves P[úu]blicas"
            + r"|^Este documento pode ser verificado no endere[çc]o eletr[ôo]nico$"
            + r"|^http://www\.in\.gov\.br/autenticidade\.html"
            + r"|^Bras[íi]lia - DF,"
            + r"|Esta edi[çc][ãa]o [ée] composta de \d+ p[áa]gina"
            + r"|^SIG, Quadra \d+, Lote \d+"
            + r"|^CNPJ: \d{14}"
            + r"|^\d{2}/\d{2}/\d{4}, \d{2}:\d{2}$"
            + r"|^SEI/[A-Z]+ - \d+ -"
            + r"|sei\.[a-z]+\.gov\.br/sei/controlador\.php",
            re.IGNORECASE,
        ),
    ),
    Regra(
        "LOCAL_ORIGEM",
        re.compile(
            r"^(Presidencia da Republica|Gabinete d[oa] Ministr[ao]|Casa Civil|Secretaria-?Geral|Subchefia para Assuntos Juridicos|Secretaria Especial para Assuntos Juridicos)$",
            re.IGNORECASE,
        ),
    ),
    # Regra mais genérica de preâmbulo, prefiro deixar elas com menos prioridade.
    Regra(
        "PREAMBULO",
        re.compile(
            r".*(no uso d(as?|e)( suas)? (atribui[çc](ao|oes)|competencias?)|que lhes? (conferem?|sao conferida|e conferida)|promulgam? a seguinte|faco saber que o Congresso Nacional decreta e eu (sanciono|promulgo)|promulgo a seguinte lei).*",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    Regra(
        "PREAMBULO",
        re.compile(r"^(Decretam?|Resolvem?(,? Ad Referendum)?)", re.IGNORECASE),
    ),
]

HEURISTICAS_PADRAO = [
    heuristica_numero_paginas,
    HeuristicaPadraoSequencia(
        tipo_alvo="DESCONHECIDO",
        novo_tipo="DENOMINACAO_AGRUPADOR",
        anterior=Sequencia(
            "AGRUPADOR", Repetir({"CONTINUACAO", "LIXO"}, min=0, max=20)
        ),
        # Pode haver notas/continuações entre a denominação e o próximo dispositivo
        # (ex.: "Subseção IV / Do Auxílio-Moradia / (Vide ...) / Art. ...").
        posterior=Sequencia(
            Repetir({"CAMPO_VIDE", "CONTINUACAO", "LIXO"}, min=0, max=20),
            Alternativas("AGRUPADOR", "ARTIGO"),
        ),
        fn_aceitacao=lambda seg, i: not seg[i].texto.lstrip().startswith("("),
    ),
    HeuristicaPadraoSequencia(
        tipo_alvo="DESCONHECIDO",
        novo_tipo="NOME_AUTORIDADE",
        posterior="TITULO_AUTORIDADE",
    ),
    HeuristicaPadraoSequencia(
        tipo_alvo="DESCONHECIDO",
        novo_tipo="NOME_AUTORIDADE",
        anterior=Alternativas("DATA", "NOME_AUTORIDADE"),
        incerto=True,
    ),
    HeuristicaPadraoSequencia(
        tipo_alvo="INICIO_BLOCO_ALTERACAO",
        novo_tipo="CONTINUACAO",
        posterior="DESCONHECIDO",
    ),
    HeuristicaPadraoSequencia(
        tipo_alvo="FIM_BLOCO_ALTERACAO",
        novo_tipo="CONTINUACAO",
        posterior="DESCONHECIDO",
    ),
    # Quando tenho um suposto titulo de normativa logo depois de um inicio de anexo, na verdade ele deve ser parte do anexo
    HeuristicaPadraoSequencia(
        tipo_alvo="TITULO_NORMATIVA", novo_tipo="TEXTO_ANEXO", anterior="INICIO_ANEXO"
    ),
    # Quando tenho um titulo de normativa entre os campos do inicio da norma e antes da norma em si, provadamente isso é só um lixo. Ocorre na Lei Orgânica da Assistência Social.
    HeuristicaPadraoSequencia(
        tipo_alvo="TITULO_NORMATIVA",
        novo_tipo="LIXO",
        anterior=Sequencia(
            Alternativas("EMENTA", "CAMPO_VIDE", "PREAMBULO", "CONSIDERANDO"),
            Repetir("CONTINUACAO", min=0),
        ),
        posterior=Alternativas("AGRUPADOR", "ARTIGO"),
    ),
    # Título de normativa em title case para casos de normas secundárias.
    HeuristicaPadraoSequencia(
        tipo_alvo="DESCONHECIDO",
        novo_tipo="TITULO_NORMATIVA",
        posterior=Alternativas("CONSIDERANDO", "EMENTA", "CAMPO_VIDE", "PREAMBULO"),
        fn_aceitacao=lambda segs, i: bool(
            re.match(
                r"^(Portaria|Resolucao|Instrucao Normativa)\b",
                strip_accents(segs[i].texto),
            )
        ),
    ),
    # Se um novo preambulo for encontrado na sequência de outro preambulo ou da continuação de um preambulo, transforma ele na continuação deste preâmbulo inicial
    HeuristicaPadraoSequencia(
        tipo_alvo="DESCONHECIDO",
        novo_tipo="PREAMBULO",
        posterior="PREAMBULO",
        # Autoridade geralmente vem em maiúsculo
        fn_aceitacao=lambda segs, i: segs[i].texto[: len(segs[i].texto) // 2].isupper(),
    ),
    # PREAMBULO logo após outro PREAMBULO (com CONTINUACAOs opcionais antes dele)
    # -> é continuação, não um preâmbulo novo.
    HeuristicaPadraoSequencia(
        tipo_alvo="PREAMBULO",
        novo_tipo="CONTINUACAO",
        anterior=Sequencia("PREAMBULO", Repetir({"CONTINUACAO"}, min=0)),
    ),
    # Pega coisas como "Da Agência Nacional..."
    HeuristicaPadraoSequencia(
        tipo_alvo="DESCONHECIDO",
        novo_tipo="DENOMINACAO_AGRUPADOR",
        anterior=Sequencia(
            Alternativas(
                "ARTIGO", "PARAGRAFO", "INCISO", "ALINEA", "ITEM", "AGRUPADOR"
            ),
            Repetir("CONTINUACAO", min=0),
        ),
        posterior=Sequencia(Repetir("DESCONHECIDO", min=0), "ARTIGO"),
        incerto=True,
        fn_aceitacao=lambda segs, i: bool(
            re.compile(r"^D[aeoAEO][sS]? .+").match(segs[i].texto)
        ),
    ),
    # Identifica "nomes penais" do Código Penal
    HeuristicaPadraoSequencia(
        tipo_alvo="DESCONHECIDO",
        novo_tipo="NOME_PENAL",
        posterior=Sequencia(
            "ARTIGO",
            Repetir(
                {"INCISO", "PARAGRAFO", "ITEM", "ALINEA"},
                min=0,
            ),
            "PENA",
        ),
        # Começa com maiúscula e não termina com pontuação
        fn_aceitacao=lambda segs, i: (
            segs[i].texto[0].isupper() and segs[i].texto[-1] not in ".;:!?"
        ),
    ),
    # Continuação específica quando o texto é simplesmente 'e', repito o tipo anterior
    HeuristicaPadraoSequencia(
        tipo_alvo="DESCONHECIDO",
        novo_tipo="CONTINUACAO",
        anterior=Alternativas("PARAGRAFO", "INCISO", "ALINEA", "ITEM", "ENUMERACAO"),
        fn_aceitacao=lambda segs, i: segs[i].texto == "e",
    ),
    # Resolve continuação de "Considerando:"
    HeuristicaPadraoSequencia(
        tipo_alvo="DESCONHECIDO",
        novo_tipo="CONTINUACAO",
        anterior=Sequencia(
            "CONSIDERANDO",
            Repetir({"CONSIDERANDO", "DESCONHECIDO", "CONTINUACAO"}, min=0, max=20),
        ),
        posterior=Sequencia(
            Repetir(
                {"CONSIDERANDO", "DESCONHECIDO", "CONTINUACAO"},
                min=0,
                max=20,
            ),
            Alternativas("PREAMBULO", "ARTIGO", "AGRUPADOR", "DENOMINACAO_AGRUPADOR"),
        ),
    ),
    # Resolve continuação de Fundamento Legal
    HeuristicaPadraoSequencia(
        tipo_alvo="DESCONHECIDO",
        novo_tipo="CONTINUACAO",
        anterior=Sequencia(
            "FUNDAMENTO_LEGAL",
            Repetir({"DESCONHECIDO", "CONTINUACAO"}, min=0, max=20),
        ),
        posterior=Sequencia(
            Repetir({"DESCONHECIDO", "CONTINUACAO"}, min=0, max=20),
            Alternativas("PREAMBULO", "ARTIGO", "AGRUPADOR", "DENOMINACAO_AGRUPADOR"),
        ),
    ),
    # Captura ementas que não caem nas expressões regulares pelo seu posicionamento no texto.
    HeuristicaPadraoSequencia(
        tipo_alvo="DESCONHECIDO",
        novo_tipo="EMENTA",
        anterior=Sequencia("TITULO_NORMATIVA", Repetir({"CAMPO_VIDE"}, min=0)),
        posterior=Sequencia(
            Repetir(
                {"CAMPO_VIDE", "CONSIDERANDO", "CONTINUACAO", "PREAMBULO"},
                min=0,
            ),
            Alternativas("ARTIGO", "AGRUPADOR", "DENOMINACAO_AGRUPADOR"),
        ),
    ),
    # Casos de parágrafos que começam sem o símbolo, só com um número ordinal.
    HeuristicaPadraoSequencia(
        tipo_alvo="DESCONHECIDO",
        novo_tipo="PARAGRAFO",
        anterior=Sequencia(
            Alternativas("ARTIGO", "PARAGRAFO", "INCISO", "ALINEA", "ITEM"),
            Repetir("CONTINUACAO", min=0),
        ),
        fn_aceitacao=lambda segs, i: bool(
            re.match(r"^\d{1,3}\.?\s*[º°oO]\s+[A-Z]", segs[i].texto)
        ),
    ),
    HeuristicaPadraoSequencia(
        tipo_alvo="DESCONHECIDO",
        novo_tipo="CONTINUACAO",
        anterior=Sequencia(
            Alternativas("ARTIGO", "INCISO", "PARAGRAFO", "ITEM", "CONTINUACAO"),
            Repetir({"LIXO"}),
        ),
    ),
    heuristica_possivel_continuacao,
    # Marco como anexo tudo que vem depois do início de um anexo que não seja o inicio de outro anexo ou o início de uma normativa.
    HeuristicaPadraoSequencia(
        tipo_alvo=lambda seg: seg.tipo in ("DESCONHECIDO", "TEXTO_ANEXO"),
        novo_tipo="TEXTO_ANEXO",
        anterior=Sequencia(Alternativas("INICIO_ANEXO", "TEXTO_ANEXO")),
    ),
    corrige_bloco_parentesis,
    HeuristicaPadraoSequencia(
        tipo_alvo="DESCONHECIDO",
        novo_tipo="ENUMERACAO",
        anterior=Alternativas(
            "ARTIGO",
            "PARAGRAFO",
            "INCISO",
            "ALINEA",
            "ITEM",
            "CONTINUACAO",
            "ENUMERACAO",
        ),
        fn_aceitacao=lambda segs, i: (
            segs[i - 1].tipo == "ENUMERACAO" or segs[i - 1].texto.rstrip().endswith(":")
        ),
    ),
    # Quando
    HeuristicaPadraoSequencia(
        tipo_alvo="DESCONHECIDO",
        novo_tipo="ENUMERACAO",
        fn_aceitacao=lambda segs, i: segs[i].texto.startswith("- "),
    ),
    heuristica_ruidos,
    heuristica_dedup_titulo,
]
