from __future__ import annotations

import re
from typing import TypeGuard

from normasbr.estrutura.modelo import (
    Agrupador,
    AlteracaoAgrupador,
    AlteracaoDispositivo,
    AlteracaoEmenta,
    BlocoAlteracao,
    ContextoAlteracaoAgrupador,
    ContextoAlteracaoDispositivo,
    Desconhecido,
    Dispositivo,
    Elemento,
    ElementoIntermediario,
    Elementos,
    Ementa,
    EmpilhavelPorTipo,
    Link,
    Normativa,
    Pena,
)
from normasbr.segmentacao.segmentador import (
    Segmento,
    strip_accents,
)


def criar_links(tups: list[tuple[str, str]]) -> list[Link]:
    return [Link(t[0], t[1]) for t in tups]


REGRAS_FILHOS: dict[type, list[type]] = {
    Agrupador: [Agrupador, Dispositivo],
    Dispositivo: [Dispositivo, BlocoAlteracao],
    BlocoAlteracao: [
        AlteracaoEmenta,
        ContextoAlteracaoAgrupador,
        AlteracaoAgrupador,
        ContextoAlteracaoDispositivo,
        AlteracaoDispositivo,
    ],
    ContextoAlteracaoAgrupador: [
        ContextoAlteracaoAgrupador,
        AlteracaoAgrupador,
    ],
    ContextoAlteracaoDispositivo: [
        ContextoAlteracaoDispositivo,
        AlteracaoDispositivo,
    ],
    AlteracaoDispositivo: [
        AlteracaoDispositivo,
    ],
    Normativa: [Agrupador, Dispositivo],
}


def aceita(pai: ElementoIntermediario, filho: Elemento) -> bool:
    tipos = REGRAS_FILHOS.get(type(pai), [])
    return any(isinstance(filho, t) for t in tipos)


USAM_TIPOS_DISPOSITIVOS = [
    Dispositivo,
    ContextoAlteracaoDispositivo,
    AlteracaoDispositivo,
]


def is_usa_tipos_dispositivo(
    elemento: Elemento,
) -> TypeGuard[Dispositivo | ContextoAlteracaoDispositivo | AlteracaoDispositivo]:
    return isinstance(elemento, tuple(USAM_TIPOS_DISPOSITIVOS))


PRIORIDADE_TIPOS_DISPOSITIVOS = {
    "artigo": 1,
    "paragrafo": 2,
    "inciso": 3,
    "alinea": 4,
    "item": 5,
}


def melhor_pai(
    elemento_atual: Elemento, stack: list[ElementoIntermediario]
) -> int | None:
    melhor_id: int | None = None

    for i in range(len(stack) - 1, -1, -1):
        pai = stack[i]

        if not aceita(pai, elemento_atual):
            continue

        pai_tem_dispositivo = is_usa_tipos_dispositivo(pai)

        if (
            is_usa_tipos_dispositivo(elemento_atual)
            and pai_tem_dispositivo
            and isinstance(pai, EmpilhavelPorTipo)
        ):
            if PRIORIDADE_TIPOS_DISPOSITIVOS.get(
                pai.tipo, 999
            ) < PRIORIDADE_TIPOS_DISPOSITIVOS.get(elemento_atual.tipo, 999):
                # Quando tem tipo de dispositivo, já posso parar o loop e aceitar
                # o valor
                return i

        if isinstance(pai, EmpilhavelPorTipo) and isinstance(
            elemento_atual, EmpilhavelPorTipo
        ):
            # Quando é do mesmo tipo, já posso parar o loop também e usar o pai desse cara
            if pai.tipo == elemento_atual.tipo:
                return i - 1

        if melhor_id is None:
            melhor_id = i

    return melhor_id


####


def obter_tipo_agrupador(texto: str) -> str:
    texto = strip_accents(texto)
    match = re.compile(
        r"^(CAPITULO|LIVRO|PARTE|SECAO|SUB-?SECAO|TITULO)", re.IGNORECASE
    ).search(texto)

    if match:
        return texto[match.start() : match.end()].lower().replace("-", "")

    # Assumo capítulo por padrão
    return "CAPITULO"


def obter_id_dispositivo(texto: str, regexp: str):
    match = re.compile(regexp, re.IGNORECASE).search(texto)
    if match:
        return texto[match.start() : match.end()]
    return ""


def obter_id_paragrafo(texto: str):
    if re.compile(r"^par[áa]grafo [uú]nico", re.IGNORECASE).match(texto):
        return "unico"

    return obter_id_dispositivo(texto, r"\d+(\-[a-z]+)?")


####

OMISSIS = re.compile(r".*[.]{4,}\s*$")

NOTA_STATUS_LINK = re.compile(
    r"^(\([^()]*\)\.?|vig[eê]ncia|regulamento|reda[cç][aã]o dada|revogado|vide)$",
    re.IGNORECASE,
)


def extrair_e_remover_parenteses_finais(s: str):
    pattern = re.compile(r"\s*(\([^()]*\))\s*$")
    removidos: list[str] = []

    while True:
        m = pattern.search(s)
        if not m:
            break
        removidos.append(m.group(1))
        s = s[: m.start()]

    return s.strip(), removidos


def substituir_ultimo(string: str, antigo: str, novo: str) -> str:
    return novo.join(string.rsplit(antigo, 1))


ESPACOS = re.compile(r"\s+")


def processar_notas_status(
    elem: Ementa | Agrupador | Dispositivo,
):
    if not elem.texto:
        return elem

    novos_links: list[Link] = []
    for link in elem.links:
        is_nota_status = bool(NOTA_STATUS_LINK.match(link.texto))

        if is_nota_status:
            elem.texto = substituir_ultimo(elem.texto, link.texto, "")
            elem.notas_status.append(link)
        else:
            novos_links.append(link)

    novo_texto, notas_sem_link = extrair_e_remover_parenteses_finais(elem.texto)

    elem.texto = novo_texto
    elem.links = novos_links
    elem.notas_status.extend([Link(n, "") for n in notas_sem_link])

    # Limpando espaços em branco
    for link in elem.links:
        link.texto = ESPACOS.sub(" ", link.texto).strip()
    for nota in elem.notas_status:
        nota.texto = ESPACOS.sub(" ", nota.texto).strip()

    return elem


def limpar_espacos(elem: Elemento) -> None:
    texto = getattr(elem, "texto", None)
    if isinstance(texto, str):
        setattr(elem, "texto", ESPACOS.sub(" ", texto).strip())


def aplicar_processamento_final(normas: list[Normativa]) -> None:
    pendentes: list[Elementos] = []
    pendentes.extend(reversed(normas))

    while pendentes:
        proximo = pendentes.pop()
        limpar_espacos(proximo)

        if isinstance(proximo, (Ementa, Agrupador, Dispositivo)):
            processar_notas_status(proximo)
        if isinstance(proximo, ElementoIntermediario):
            pendentes.extend(proximo.filhos)


def converter(seg: Segmento):
    match seg.tipo:
        case "TITULO_NORMATIVA":
            origem = seg.obter_origem()
            return Normativa(nome=seg.texto, origem=origem)
        case "EMENTA":
            return Ementa(
                texto=seg.texto,
                efetivo=not seg.is_riscado(),
                links=criar_links(seg.obter_links()),
            )
        case "INICIO_BLOCO_ALTERACAO":
            return BlocoAlteracao()
        case "ARTIGO":
            return Dispositivo(
                tipo="artigo",
                texto=seg.texto,
                id=obter_id_dispositivo(seg.texto, r"\d+(\.\d{3})*(\-[a-z]+)?"),
                efetivo=not seg.is_riscado(),
                links=criar_links(seg.obter_links()),
            )
        case "PARAGRAFO":
            return Dispositivo(
                tipo="paragrafo",
                texto=seg.texto,
                id=obter_id_paragrafo(seg.texto),
                efetivo=not seg.is_riscado(),
                links=criar_links(seg.obter_links()),
            )
        case "INCISO":
            return Dispositivo(
                tipo="inciso",
                texto=seg.texto,
                id=obter_id_dispositivo(seg.texto, r"[MDCLXVI]+(\-[a-z]+)?"),
                efetivo=not seg.is_riscado(),
                links=criar_links(seg.obter_links()),
            )
        case "ALINEA":
            return Dispositivo(
                tipo="alinea",
                texto=seg.texto,
                id=obter_id_dispositivo(seg.texto, r"[a-z]+(\-[a-z]+)?"),
                efetivo=not seg.is_riscado(),
                links=criar_links(seg.obter_links()),
            )
        case "ITEM":
            return Dispositivo(
                tipo="item",
                texto=seg.texto,
                id=obter_id_dispositivo(seg.texto, r"\d+(\-[a-z]+)?"),
                efetivo=not seg.is_riscado(),
                links=criar_links(seg.obter_links()),
            )
        case "AGRUPADOR":
            return Agrupador(
                id=seg.texto,
                tipo=obter_tipo_agrupador(seg.texto),
                efetivo=not seg.is_riscado(),
                links=criar_links(seg.obter_links()),
            )
        case "DESCONHECIDO":
            return Desconhecido()
        case "PENA":
            return Pena(texto=seg.texto, links=criar_links(seg.obter_links()))
        # Casos especiais, tratados posteriormente
        case (
            "FIM_BLOCO_ALTERACAO"
            | "CONTINUACAO"
            | "ENUMERACAO"
            | "DENOMINACAO_AGRUPADOR"
            | "PREAMBULO"
        ):
            pass
        # Casos não tratados
        case (
            "OMISSIS"
            | "TITULO_AUTORIDADE"
            | "INICIO_ANEXO"
            | "TEXTO_ANEXO"
            | "DATA"
            | "LIXO"
            | "LOCAL_ORIGEM"
            | "NOME_AUTORIDADE"
            | "CAMPO_VIDE"
        ):
            pass


def estruturar(segmentos: list[Segmento], leniente: bool = False) -> list[Normativa]:
    stack: list[ElementoIntermediario] = []
    normativas: list[Normativa] = []

    ja_imprimiu_origem = False
    ultimo_bloco_nao_empilhavel = None
    nome_penal_pendente: str | None = None
    dentro_anexo: bool = False
    for seg in segmentos:
        elemento_atual = converter(seg)

        # ===== Casos especiais =====
        if isinstance(elemento_atual, Normativa):
            normativa = elemento_atual
            stack = [normativa]
            normativas.append(normativa)

            # Reseto tipo de anexo
            if dentro_anexo:
                dentro_anexo = False

            continue

        # Caso tenha passado pelo if anterior, e não existe
        # uma norma ainda, sinal que o documento começou errado...
        if not len(stack):
            # print(f"Sem Início da Normativa: {seg.obter_origem()}")
            continue
            # normativa_dummy = Normativa(
            #     nome="Normativa Desconhecida", origem=seg.obter_origem()
            # )
            # stack = [normativa_dummy]
            # normativas.append(normativa_dummy)

        # Se dentro do anexo, consumo tudo sem fazer nada
        if dentro_anexo:
            continue

        if isinstance(elemento_atual, Ementa):
            if stack and isinstance(stack[0], Normativa):
                stack[0].ementa += [elemento_atual]
                ultimo_bloco_nao_empilhavel = "EMENTA"

            # else:
            #     print("Ementa sem normativa iniciada")
            continue

        if seg.tipo == "PREAMBULO":
            if stack and isinstance(stack[0], Normativa):
                stack[0].preambulo = seg.texto
                ultimo_bloco_nao_empilhavel = "PREAMBULO"

            # else:
            #     print("Preambulo sem normativa iniciada")
            continue

        if seg.tipo == "NOME_PENAL":
            nome_penal_pendente = seg.texto
            continue

        if seg.tipo in ("CONTINUACAO", "ENUMERACAO"):
            anterior = stack[-1]
            texto_anterior = getattr(anterior, "texto", None)
            if texto_anterior is not None:
                setattr(anterior, "texto", texto_anterior + " " + seg.texto)
            elif isinstance(anterior, Normativa):
                if ultimo_bloco_nao_empilhavel == "EMENTA":
                    anterior.ementa[-1].texto += " " + seg.texto
                elif (
                    ultimo_bloco_nao_empilhavel == "PREAMBULO"
                    and anterior.preambulo is not None
                ):
                    anterior.preambulo += " " + seg.texto

            continue

        # Zera ultimo bloco não empilhável.
        ultimo_bloco_nao_empilhavel = None

        if seg.tipo == "INICIO_ANEXO":
            dentro_anexo = True
            continue

        if seg.tipo == "DENOMINACAO_AGRUPADOR":
            anterior = stack[-1]
            if isinstance(anterior, Agrupador):
                anterior.texto = seg.texto
            else:
                stack.append(Agrupador(id=seg.texto, texto=seg.texto, tipo="capitulo"))
            continue

        pos_bloco_alteracao = next(
            iter([i for i, e in enumerate(stack) if isinstance(e, BlocoAlteracao)]),
            None,
        )

        if seg.tipo == "INICIO_BLOCO_ALTERACAO" and pos_bloco_alteracao:
            # print("Abertura de bloco de alteração num bloco já aberto")
            continue

        if seg.tipo == "FIM_BLOCO_ALTERACAO":
            if not pos_bloco_alteracao:
                pass
                # print("Finalização de Bloco de Alteração sem um início.")
            else:
                stack = stack[:pos_bloco_alteracao]
            continue

        if elemento_atual is None:
            continue

        if isinstance(elemento_atual, Desconhecido):
            if not ja_imprimiu_origem:
                # print()
                # print(f"[Documento: {seg.obter_origem()}]")
                ja_imprimiu_origem = True

            # print(f"\tDesconhecido: {seg.texto}")
            continue

        # Pena é terminal: anexar ao dispositivo conteiner (artigo/parágrafo)
        # mais próximo na pilha, como irmão dos incisos.
        if isinstance(elemento_atual, Pena):
            for j in range(len(stack) - 1, -1, -1):
                pai = stack[j]
                if isinstance(
                    pai, (Dispositivo, AlteracaoDispositivo)
                ) and pai.tipo in {
                    "artigo",
                    "paragrafo",
                }:
                    pai.filhos.append(elemento_atual)
                    break
            continue

        # ====== Alteração ==========
        if pos_bloco_alteracao:
            if isinstance(elemento_atual, Dispositivo):
                if OMISSIS.match(elemento_atual.texto.strip()):
                    elemento_atual = ContextoAlteracaoDispositivo(
                        tipo=elemento_atual.tipo,
                        id=elemento_atual.id,
                    )
                else:
                    elemento_atual = AlteracaoDispositivo(
                        tipo=elemento_atual.tipo,
                        texto=elemento_atual.texto,
                        id=elemento_atual.id,
                    )

            if isinstance(elemento_atual, Agrupador):
                texto = (
                    elemento_atual.texto if elemento_atual.texto else elemento_atual.id
                )
                if OMISSIS.match(texto):
                    elemento_atual = ContextoAlteracaoAgrupador(
                        tipo=elemento_atual.tipo,
                        id=elemento_atual.id,
                    )
                else:
                    elemento_atual = AlteracaoAgrupador(
                        tipo=elemento_atual.tipo,
                        texto=elemento_atual.texto,
                        id=elemento_atual.id,
                    )

        if nome_penal_pendente is not None and isinstance(
            elemento_atual, (Dispositivo, AlteracaoDispositivo, Agrupador)
        ):
            # Somente adiciono o tipo o nome penal ao artigo que vier após ele
            if getattr(elemento_atual, "tipo", "") == "artigo":
                elemento_atual.nome_penal = nome_penal_pendente  # pyright: ignore[reportAttributeAccessIssue]
            nome_penal_pendente = None

        #  ===== Casos gerais =====

        pai_id = melhor_pai(elemento_atual, stack)
        if pai_id is None:
            # Debug
            # for s in stack:
            #     print(s)
            #     print()

            msg = f"Não foi possível processar: {seg!r}"
            if not leniente:
                raise Exception(msg)
            else:
                # print(msg)
                continue

        stack[pai_id].filhos += [elemento_atual]
        stack = stack[: pai_id + 1]
        # Todos os terminais foram tratados com continue acima; só intermediários chegam aqui.
        # assert isinstance(elemento_atual, ElementoIntermediario)
        stack.append(elemento_atual)

    normativas = [n for n in normativas if len(n.filhos)]
    aplicar_processamento_final(normativas)
    return normativas
