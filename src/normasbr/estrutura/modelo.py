from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import BaseModel, Field

TiposDispositivos = Literal["artigo", "paragrafo", "inciso", "alinea", "item"]


@dataclass()
class Link:
    """Trecho de texto com o link de onde foi extraído."""

    texto: str
    url: str


class Elemento(BaseModel):
    """Base de todo elemento da árvore; ``classe`` identifica o tipo concreto."""

    classe: str = ""
    links: list[Link] = []


class ElementoTerminal(Elemento):
    """Elemento que não possui filhos."""


class ElementoIntermediario(Elemento):
    """Elemento que pode conter outros elementos em ``filhos``."""

    filhos: list[Elementos] = []


class Modificavel(BaseModel):
    """Elemento com marcação de vigência (``efetivo`` e ``notas_status``)."""

    notas_status: list[Link]
    efetivo: bool


class EmpilhavelPorTipo(BaseModel):
    """Elemento cuja posição na hierarquia depende do ``tipo``."""

    tipo: str


######


class Ementa(Modificavel, ElementoTerminal):
    """Resumo do objeto da normativa."""

    classe: Literal["ementa"] = "ementa"  # pyright: ignore[reportIncompatibleVariableOverride]
    texto: str = ""

    efetivo: bool = True
    notas_status: list[Link] = []


class AlteracaoEmenta(ElementoTerminal):
    """Nova ementa dentro de um bloco de alteração."""

    classe: Literal["alteracao_ementa"] = "alteracao_ementa"  # pyright: ignore[reportIncompatibleVariableOverride]
    texto: str = ""


class AlteracaoAgrupador(ElementoTerminal):
    """Agrupador alterado por um bloco de alteração."""

    classe: Literal["alteracao_agrupador"] = "alteracao_agrupador"  # pyright: ignore[reportIncompatibleVariableOverride]
    id: str = ""
    tipo: str = ""
    texto: str | None = None


class Desconhecido(ElementoTerminal):
    """Segmento que não pôde ser classificado."""

    classe: Literal["desconhecido"] = "desconhecido"  # pyright: ignore[reportIncompatibleVariableOverride]


########


class BlocoAlteracao(ElementoIntermediario):
    """Trecho entre aspas que altera outra normativa."""

    classe: Literal["bloco_alteracao"] = "bloco_alteracao"  # pyright: ignore[reportIncompatibleVariableOverride]
    filhos: list[Elementos] = []


class ContextoAlteracaoAgrupador(EmpilhavelPorTipo, ElementoIntermediario):
    """Agrupador citado só para contextualizar uma alteração."""

    classe: Literal["contexto_alteracao_agrupador"] = "contexto_alteracao_agrupador"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: str = ""
    tipo: str = ""

    filhos: list[Elementos] = []


class ContextoAlteracaoDispositivo(ElementoIntermediario, EmpilhavelPorTipo):
    """Dispositivo citado só para contextualizar uma alteração."""

    classe: Literal["contexto_alteracao_dispositivo"] = "contexto_alteracao_dispositivo"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: str = ""
    tipo: str = ""

    filhos: list[Elementos] = []


class AlteracaoDispositivo(ElementoIntermediario, EmpilhavelPorTipo):
    """Dispositivo alterado por um bloco de alteração."""

    classe: Literal["alteracao_dispositivo"] = "alteracao_dispositivo"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: str = ""
    tipo: str = ""
    texto: str = ""
    nome_penal: str | None = None

    filhos: list[Elementos] = []


######


class Agrupador(Modificavel, EmpilhavelPorTipo, ElementoIntermediario):
    """Capítulo, seção, título ou outro agrupador de dispositivos."""

    classe: Literal["agrupador"] = "agrupador"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: str = ""
    tipo: str = ""
    texto: str | None = None

    efetivo: bool = True
    notas_status: list[Link] = []

    filhos: list[Elementos] = []


class Dispositivo(Modificavel, EmpilhavelPorTipo, ElementoIntermediario):
    """Artigo, parágrafo, inciso, alínea ou item."""

    classe: Literal["dispositivo"] = "dispositivo"  # pyright: ignore[reportIncompatibleVariableOverride]

    tipo: str = ""
    id: str = ""
    texto: str = ""
    nome_penal: str | None = None

    efetivo: bool = True
    notas_status: list[Link] = []

    filhos: list[Elementos] = []


class Pena(ElementoTerminal):
    """Pena associada a um artigo ou parágrafo."""

    classe: Literal["pena"] = "pena"  # pyright: ignore[reportIncompatibleVariableOverride]

    texto: str = ""


class Normativa(ElementoIntermediario):
    """Raiz da árvore: uma norma completa."""

    classe: Literal["norma"] = "norma"  # pyright: ignore[reportIncompatibleVariableOverride]

    nome: str = ""
    preambulo: str | None = None
    ementa: list[Ementa] = []

    filhos: list[Elementos] = []
    origem: str = ""


Elementos = Annotated[
    Ementa
    | AlteracaoEmenta
    | AlteracaoAgrupador
    | BlocoAlteracao
    | ContextoAlteracaoAgrupador
    | ContextoAlteracaoDispositivo
    | AlteracaoDispositivo
    | Agrupador
    | Dispositivo
    | Pena
    | Normativa,
    Field(discriminator="classe"),
]
