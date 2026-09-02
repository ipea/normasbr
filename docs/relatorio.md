# Relatório

> Este relatório foi escrito num editor de texto com corretor ortográfico e sem assistência de LLMs.

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

Ao receber os blocos da etapa anterior, o segmentador é responsável por separar os blocos em unidades atômicas e classificá-las em categorias predeterminadas. Na analogia com compiladores de linguagens de programação, esta etapa seria a análise léxica, ou "tokenização".

As categorias usadas para classificar os blocos foram baseadas tanto em diversas normativas testadas, quanto no [Glossário e técnica legislativa do Congresso Nacional](https://www.congressonacional.leg.br/legislacao-e-publicacoes/glossario-tecnica-legislativa). Até a escrita deste relatório, existem as seguintes categorias: desconhecido, titulo da normativa, inicio do bloco de alteração, considerando, artigo, paragrafo, inciso, alineá, item, ementa, continuação, enumeração, fim do bloco de alteração, preambulo, campo vide, agrupador, denominação do agrupador, omissis, titulo da autoridade, inicio do anexo, data, lixo, local origem, texto anexo, nome autoridade, nome penal, pena, fundamento legal.

Tipicamente, o Segmentador considera cada bloco recebido da etapa anterior, Extração de Blocos, como um segmento. As únicas exceções atuais são a abertura e o fechamento de blocos de alteração, identificados pela presença de aspas em determinadas posições, que são separadas em segmentos próprios.

Após a identificação dos segmentos, o segmentador tenta classificá-las nas categorias supramencionadas, valendo-se de dois componentes chamados Regras e Heurísticas. As Regras são a primeira etapa, elas consistem de uma expressão regular e a sua categoria. Quando a expressão regular casa com o texto do segmento atual, o segmento recebe a classificação informada pela Regra, e ignora as demais regras. Os segmentos que não casaram nenhuma vez são categorizados como "desconhecido". Um exemplo de Regra poderia ser descrito como: se o texto do bloco começa com "Parágrafo único" ou "§", então o bloco é classificado como "parágrafo".

Tendo os segmentos parcialmente classificados, o Segmentador agora utiliza as chamadas Heurísticas para aprimorar as categorizações já feitas. Elas utilizam lógicas mais complexas, levando em consideração toda a sequência de blocos para realizar a tarefa. Alguns exemplos de heurísticas são: quando que títulos de normas aparecem mais de uma vez, classificar as ocorrências seguintes como "lixo", já que provavelmente tratam-se do cabeçalho do documento; quando um bloco "desconhecido" estiver depois de um título de normativa e antes dos blocos classificados como "preâmbulo", "campo vide" e "considerando", classificá-lo como "ementa".

### Estruturação dos Segmentos

Com os segmentos já classificados, a etapa seguinte consiste em processá-los de forma a reconstruir a estrutura hierárquica das normas. Esta etapa seria similar à análise sintática dos compiladores.

O Estruturador tenta construir tal hierarquia convertendo a sequência de segmentos numa árvore hierárquica com elementos próprios, levando em consideração as classificações e as regras de composição dos vários tipos de elementos. A saber, existem atualmente as seguintes categorias de elementos: Normativa, Ementa, Agrupador, Dispositivo, Pena, Alteração de Ementa, Alteração de Agrupador, Alteração de Dispositivo, Bloco de Alteração, Agrupador para Contexto de Alteração e Dispositivo para Contexto de Alteração.

Cada categoria de elementos mencionada acima pode ser compreendida em dois grupos: os elementos intermediários e os elementos finais. Elementos intermediários, como Normativas, Agrupadores, ou Dispositivos, podem conter outros elementos intermediários ou elementos finais. Já os elementos finais, como Ementas, Pena, Alteração de Agrupador, não podem conter elementos filhos. Tal lógica de elementos intermediários e finais, junto com restrições extras sobre quais categorias de elementos podem ser compostos com quais outras, e o uso da estrutura de dados "stack" (pilha), formam o núcleo lógico do Estruturador.

TODO: TERMINAR EXEMPLO!!

Para exemplificar o funcionamento do Estruturador, considera-se que já exista na pilha de elementos processados: uma Normativa, um Agrupador de Capítulo, um Agrupador de Sessão, um Dispositivo de Artigo e um Dispositivo de Parágrafo. Os próximos elemento a serem processado serão um Dispositivo de Inciso, um Dispositivo de Parágrafo e um Agrupador de Sessão.

A estrutura atual pode ser visualizada assim:

```
Pilha:

Normativa
 └── Agrupador de Capítulo
  └──
└──
```

Ao tentar processar o inciso, o Estruturador observa: que o último elemento na pilha é um Parágrafo, que Dispositivos podem ser filhos de outros Dispositivos, e que não existe outro Dispositivo de Inciso atualmente na pilha. Com isso, ele toma a decisão de incluir o inciso como um elemento filho do parágrafo e adiciona esse inciso na pilha.

```

```

No processamento do elemento seguinte, um Dispositivo de Parágrafo, o Estruturador observa uma situação bem similar à anterior, entretanto já existe outro Dispositivo de Parágrafo na pilha. Ele então remove da pilha tanto o Inciso quanto o Parágrafo já existente, adicionando o parágrafo novo como filho do elemento anterior, o Dispositivo de Artigo, e também o adiciona o novo Parágrafo na pilha.

```

```

AAAAAAAAAA

```

```

Observa-se que o Estruturador não precisa levar em consideração a ordem esperada dos vários tipos de dispositivos (artigo, paragrafo, inciso, item) ou de agrupadores (livro, capítulo, seção), o que tem a vantagem de simplificar o código, não tornar a estruturação rígida, e manter a possibilidade de se representar normas formatadas fora do padrão usual. Além disso, quando um elemento não pode ser inserido na árvore sem violar alguma das regras supracitadas, ele provavelmente se trata de um trecho problemático da norma ou algum artefato do documento, como uma numeração de páginas em um PDF, e pode ser descartado sem grandes perdas.

Para fins de melhoria na qualidade de dados, alguns processamentos extras são feitos. Por exemplo, alguns segmentos descartados sumariamente nesta etapa, como os classificados como "Lixo" ou "Desconhecido". Segmentos dentro de anexos, mesmo que contenham dispositivos legais, atualmente também são descartados, já que necessitariam de uma lógica mais robusta para identificar se eles formam uma norma bem comportada, afim de não adicionar ruído no resultado final. O Estruturador também tenta fundir os textos presentes em sequências de segmentos de "continuação", e remove os trechos entre parênteses que ocorrem no final dos dispositivos, que ainda são salvos como uma "nota de status" daquele dispositivo. Essas notas tipicamente indicam qual outro normativo alterou aquele trecho.

O resultado final da estruturação pode ser salvo num arquivo usando o conhecido formato textual `yaml`, para uma fácil visualização humana e manipulação por máquina. Vide o exemplo abaixo do formato `yaml`.

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

## Classificação Textual dos Dispositivos

Art. 39. O operador deverá realizar o tratamento segundo as instruções fornecidas pelo controlador, que verificará a observância das próprias instruções e das normas sobre a matéria.

LEI Nº 13.709, DE 14 DE AGOSTO DE 2018
Ementa: Lei Geral de Proteção de Dados Pessoais (LGPD).
CAPÍTULO VI - DOS AGENTES DE TRATAMENTO DE DADOS PESSOAIS
Seção I - Do Controlador e do Operador

## Uso de LLMs

## Desenvolvimento

## Limitações e trabalhos futuros

- Identificação de referências
- Resolução de referências
- Uso de um id canônico
- Heurística de qualidade de norma
- Uso de algoritmo determinístico vs probabilístico
