# Relatório

## Resumo

Este relatório descreve o funcionamento do pacote Python `normasbr` para estruturação de textos normativos brasileiros nos mais diversos formatos. Seu objetivo é processar os textos das normas afim de se criar uma detalhada representação hierárquica delas, para então realizar outras análises, como classificação ou agrupamento de dispositivos, e permitindo que o usuário consiga utilizar a melhor representação para auxiliar em sua análise.

## Motivação

Com o objetivo inicial de realizar classificações textuais dos artigos de diversas normativas brasileiras, desde trechos da constituição federal até portarias ministeriais publicadas no Diário Oficial da União, foi realizada uma segmentação "ad hoc" de seus artigos, baseada somente em palavras-chave. Entretanto, notou-se que tal segmentação simplificada deixava a desejar, além de não manter contexto suficiente para se realizar a classificação adequadamente em alguns casos, especialmente quando os artigos são muito sucintos. Além disso, algumas normativas são disponibilizadas somente em formato PDF, que não é facilmente convertido para texto bruto, além de possuir diversos elementos que não fazem parte do corpo principal do documento, como cabeçalhos, número da paginas etc. Tais elementos adicionam ruídos e podem atrapalhar etapas posteriores da análise.

Para se superar tais desafios, foi desenvolvido um pacote em Python que busca fazer o tratamento das normativas de forma robusta nos mais diversos formatos de arquivos, gerando como resultado uma estrutura hierárquica facilmente manipulável por código, na qual o usuário é capaz de facilmente obter as informações necessárias para as etapas subsequentes que desejar fazer.

## Abordagem da Estruturação das normas

Para se processar os textos normativos, são realizadas quatro etapas, em parte inspiradas no funcionamento de compiladores de linguagens de programação:

- Ingestão do arquivo de entrada, convertendo o para HTML;
- Extração dos blocos de texto do HTML;
- Segmentação dos blocos;
- Estruturação dos segmentos;

A modelagem tanto da segmentação quanto da estruturação, foram baseadas em

### Ingestão de Arquivos

Na ingestão, o pacote tenta converter o arquivo recebido em algum dos formatos aceitos (pdf, html, docx, txt) para HTML, que será usado como formato canônico nos processamentos posteriores, o que facilita a manutenção e adição de novos formatos no futuro.

Para se converter os formatos `pdfs` e `docx`, foram usadas, respectivamente, as consolidadas bibliotecas de Python `pymupdf` e `mammoth`. Arquivos em formato `txt` são convertidos internamente adicionando-se o preâmbulo esperado do HTML e uma tag de paragrafo para cada linha do arquivo original.

### Extração de Blocos

A extração de blocos consiste em coletar, do HTML gerado na etapa anterior, os trechos de texto que serão usados nos processamentos posteriores, mantendo algumas informações de formatação que pode ser úteis, por exemplo, quando o texto está tachado, o que é um indício de um dispositivo revogado. Esta etapa ainda tenta corrigir alguns problemas comuns encontrados nos HTMLs do [planalto.gov.br](planalto.gov.br), como tags mal formatadas.

### Segmentador de Blocos

Ao receber os blocos da etapa anterior, o segmentador é responsável por separar os blocos em unidades atômicas e classificá-las em categorias predeterminadas. Na analogia com compiladores de linguagens de programação, esta etapa seria a análise léxica, ou tokenização.

Até a escrita deste relatório, os blocos são classificados nas seguintes categorias: desconhecido, titulo da normativa, inicio do bloco de alteração, considerando, artigo, paragrafo, inciso, alineá, item, ementa, continuação, enumeração, fim do bloco de alteração, preambulo, campo vide, agrupador, denominação do agrupador, omissis, titulo da autoridade, inicio do anexo, data, lixo, local origem, texto anexo, nome autoridade, nome penal, pena, fundamento legal. Esta modelagem dos blocos é baseada tanto nas normativas testadas quanto no [Glossário e técnica legislativa do Congresso Nacional](https://www.congressonacional.leg.br/legislacao-e-publicacoes/glossario-tecnica-legislativa).

### Estruturação dos Segmentos

O resultado final é dado em um arquivo no formato `yaml`, como no exemplo abaixo.

```yaml
- classe: norma
  nome: LEI COMPLEMENTAR Nº 210, DE 25 DE NOVEMBRO DE 2024
  origem: data/novas/lei-complementar-210-2024.html
  ementa:
    - classe: ementa
      efetivo: true
      texto:
        Dispõe sobre a proposição e a execução de emendas parlamentares na lei
        orçamentária anual; e dá outras providências.
  preambulo:
    "O PRESIDENTE DA REPÚBLICA Faço saber que o Congresso Nacional decreta
    e eu sanciono a seguinte Lei Complementar:"
  filhos:
    - classe: agrupador
      tipo: capitulo
      id: CAPÍTULO I
      efetivo: true
      texto: DO OBJETO
      filhos:
        - classe: dispositivo
          tipo: artigo
          id: "1"
          efetivo: true
          texto:
            Art. 1º A proposição e a execução das emendas parlamentares à despesa,
            no âmbito da lei orçamentária anual da União, observarão o disposto nesta
            Lei Complementar, nos termos dos incisos I e III do § 9º do art. 165 da Constituição
            Federal.
          links:
            - texto: incisos I
              url: ../../Constituicao/Constituicao.htm#art165§9i
            - texto: III do § 9º do art. 165 da Constituição Federal.
              url: ../../Constituicao/Constituicao.htm#art165§9iii.0
          filhos:
            - classe: dispositivo
              tipo: paragrafo
              id: unico
              efetivo: true
              texto:
                Parágrafo único. O regramento disposto nesta Lei Complementar é imperativo
                para as leis orçamentárias previstas na Constituição Federal, bem como para
                a interpretação e a aplicação dos demais instrumentos normativos sobre a
                temática.
```

## Abordagem da Classificação dos Dispositivos

## Uso de LLMs

## Desenvolvimento

## Limitações
