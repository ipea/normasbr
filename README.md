# normasbr

[![MIT licensed](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](./pyproject.toml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**normasbr** é uma biblioteca Python que extrai, segmenta e estrutura normativas
brasileiras (leis, decretos, medidas provisórias etc.) a partir de HTML, PDF, DOCX ou
TXT, convertendo textos brutos do [Planalto](https://www4.planalto.gov.br/legislacao)
em documentos estruturados (YML), com hierarquia completa de dispositivos
(norma > agrupadores > artigos > incisos > alíneas > itens).

O processamento é determinístico, usando heurísticas e expressões regulares baseadas em documentos normativos diversos.

## Pipeline

```
ingerir -> segmentar -> estruturar
```

1. **Ingestão**: normaliza HTML/PDF/DOCX/TXT para um HTML canônico;
2. **Segmentação**: extrai blocos de texto e classifica cada segmento
   (artigo, parágrafo, inciso, ementa, preâmbulo, bloco de alteração etc.);
3. **Estruturação**: monta a árvore hierárquica da normativa a partir dos segmentos;

## Instalação

A última versão pode ser instalada com o [uv](https://docs.astral.sh/uv/):

```bash
uv add normasbr # Usando como biblioteca
uv tool install normasbr # Usando como utilitário de linha de comando
```

Ou diretamente do repositório:

```bash
uv pip install git+https://github.com/ipea/normasbr
```

## Exemplo de uso

### Biblioteca:

```python
import normasbr

for bruta in normasbr.despachar_ingestao("data/DEL5452.htm"):
    segmentos = normasbr.Segmentador().segmentar(normasbr.extrair_blocos(bruta))
    normas = normasbr.estruturar(segmentos, leniente=True)

print(normasbr.formatar_normativas_yml(normas))
```

### CLI:

```bash
normasbr ingerir data/DEL5452.htm
normasbr segmentar data/docs
normasbr estruturar data/docs -o normas.yml
normasbr diff_seg snapshot.jsonl novo.jsonl
normasbr classificar_macrodim normas.yml saida.parquet
normasbr classificar_anomalias normas.yml
```

## Desenvolvimento

```bash
make setup   # cria o venv e instala as dependências
make check   # lint (ruff) + testes (pytest)
make format  # formata o código
```

## Referências usadas na modelagem

- [Glossário e técnica legislativa do Congresso Nacional](https://www.congressonacional.leg.br/legislacao-e-publicacoes/glossario-tecnica-legislativa)

## Nota <a href="https://www.ipea.gov.br"><img src="https://www.ipea.gov.br/themes/custom/ipea_theme/logo.svg" alt="Ipea" align="right" width="200"/></a>

**normasbr** é desenvolvido por uma equipe de pesquisadores do Instituto de Pesquisa
Econômica Aplicada (Ipea).
