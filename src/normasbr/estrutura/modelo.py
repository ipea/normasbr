from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import BaseModel, Field

TiposDispositivos = Literal["artigo", "paragrafo", "inciso", "alinea", "item"]


@dataclass()
class Link:
    texto: str
    url: str


class Elemento(BaseModel):
    classe: str = ""
    links: list[Link] = []


class ElementoTerminal(Elemento):
    pass


class ElementoIntermediario(Elemento):
    filhos: list[Elementos] = []


class Modificavel(BaseModel):
    notas_status: list[Link]
    efetivo: bool


class EmpilhavelPorTipo(BaseModel):
    tipo: str


######


class Ementa(Modificavel, ElementoTerminal):
    classe: Literal["ementa"] = "ementa"  # pyright: ignore[reportIncompatibleVariableOverride]
    texto: str = ""

    efetivo: bool = True
    notas_status: list[Link] = []


class AlteracaoEmenta(ElementoTerminal):
    classe: Literal["alteracao_ementa"] = "alteracao_ementa"  # pyright: ignore[reportIncompatibleVariableOverride]
    texto: str = ""


class AlteracaoAgrupador(ElementoTerminal):
    classe: Literal["alteracao_agrupador"] = "alteracao_agrupador"  # pyright: ignore[reportIncompatibleVariableOverride]
    id: str = ""
    tipo: str = ""
    texto: str | None = None


class Desconhecido(ElementoTerminal):
    classe: Literal["desconhecido"] = "desconhecido"  # pyright: ignore[reportIncompatibleVariableOverride]


########


class BlocoAlteracao(ElementoIntermediario):
    classe: Literal["bloco_alteracao"] = "bloco_alteracao"  # pyright: ignore[reportIncompatibleVariableOverride]
    filhos: list[Elementos] = []


class ContextoAlteracaoAgrupador(EmpilhavelPorTipo, ElementoIntermediario):
    classe: Literal["contexto_alteracao_agrupador"] = "contexto_alteracao_agrupador"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: str = ""
    tipo: str = ""

    filhos: list[Elementos] = []


class ContextoAlteracaoDispositivo(ElementoIntermediario, EmpilhavelPorTipo):
    classe: Literal["contexto_alteracao_dispositivo"] = "contexto_alteracao_dispositivo"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: str = ""
    tipo: str = ""

    filhos: list[Elementos] = []


class AlteracaoDispositivo(ElementoIntermediario, EmpilhavelPorTipo):
    classe: Literal["alteracao_dispositivo"] = "alteracao_dispositivo"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: str = ""
    tipo: str = ""
    texto: str = ""
    nome_penal: str | None = None

    filhos: list[Elementos] = []


######


class Agrupador(Modificavel, EmpilhavelPorTipo, ElementoIntermediario):
    classe: Literal["agrupador"] = "agrupador"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: str = ""
    tipo: str = ""
    texto: str | None = None

    efetivo: bool = True
    notas_status: list[Link] = []

    filhos: list[Elementos] = []


class Dispositivo(Modificavel, EmpilhavelPorTipo, ElementoIntermediario):
    classe: Literal["dispositivo"] = "dispositivo"  # pyright: ignore[reportIncompatibleVariableOverride]

    tipo: str = ""
    id: str = ""
    texto: str = ""
    nome_penal: str | None = None

    efetivo: bool = True
    notas_status: list[Link] = []

    filhos: list[Elementos] = []


class Pena(ElementoTerminal):
    classe: Literal["pena"] = "pena"  # pyright: ignore[reportIncompatibleVariableOverride]

    texto: str = ""


class Normativa(ElementoIntermediario):
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
