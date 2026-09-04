# Relatório

> Este relatório foi escrito num editor de texto com corretor ortográfico e sem assistência de LLMs.

## Resumo

Este relatório descreve o funcionamento do pacote Python `normasbr` para estruturação de textos normativos brasileiros nos mais diversos formatos. Seu objetivo é processar os textos das normas a fim de se criar uma detalhada representação hierárquica delas, para então realizar outras análises, como classificação ou agrupamento de dispositivos, e permitindo que o usuário consiga utilizar a melhor representação para auxiliar em sua análise.

## Motivação

Com o objetivo inicial de realizar classificações textuais dos artigos de diversas normativas brasileiras, desde trechos da constituição federal até portarias ministeriais publicadas no Diário Oficial da União, foi realizada uma segmentação "ad hoc" de seus artigos, baseada somente em palavras-chave. Entretanto, notou-se que tal segmentação simplificada era suficiente, além de não manter contexto suficiente para se realizar a classificação adequadamente em alguns casos, especialmente quando os artigos são muito sucintos. Além disso, algumas normativas são disponibilizadas somente em formato PDF, que não é facilmente convertido para texto bruto, além de possuir diversos elementos que não fazem parte do corpo principal do documento, como cabeçalhos, número da páginas etc. Tais elementos adicionam ruídos e podem atrapalhar etapas posteriores da análise.

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

A extração de blocos consiste em coletar, do HTML gerado na etapa anterior, os trechos de texto que serão usados nos processamentos posteriores, mantendo algumas informações de formatação que podem ser úteis, por exemplo, quando o texto está tachado, o que é um indício de um dispositivo revogado. Esta etapa ainda tenta corrigir alguns problemas comuns encontrados nos HTMLs do [planalto.gov.br](planalto.gov.br), como tags mal formatadas.

### Segmentador de Blocos

Ao receber os blocos da etapa anterior, o segmentador é responsável por separar os blocos em unidades atômicas e classificá-las em categorias predeterminadas. Na analogia com compiladores de linguagens de programação, esta etapa seria a análise léxica, ou "tokenização".

As categorias usadas para classificar os blocos foram baseadas tanto em diversas normativas testadas, quanto no [Glossário e técnica legislativa do Congresso Nacional](https://www.congressonacional.leg.br/legislacao-e-publicacoes/glossario-tecnica-legislativa). Até a escrita deste relatório, existem as seguintes categorias: desconhecido, título da normativa, início do bloco de alteração, considerando, artigo, paragrafo, inciso, alínea, item, ementa, continuação, enumeração, fim do bloco de alteração, preambulo, campo vide, agrupador, denominação do agrupador, omissis, título da autoridade, início do anexo, data, lixo, local origem, texto anexo, nome autoridade, nome penal, pena, fundamento legal.

Tipicamente, o Segmentador considera cada bloco recebido da etapa anterior, Extração de Blocos, como um segmento. As únicas exceções atuais são a abertura e o fechamento de blocos de alteração, identificados pela presença de aspas em determinadas posições, que são separadas em segmentos próprios.

Após a identificação dos segmentos, o segmentador tenta classificá-las nas categorias supramencionadas, valendo-se de dois componentes chamados Regras e Heurísticas. As Regras são a primeira etapa, elas consistem em uma expressão regular e a sua categoria. Quando a expressão regular casa com o texto do segmento atual, o segmento recebe a classificação informada pela Regra, e ignora as demais regras. Os segmentos que não casaram nenhuma vez são categorizados como "desconhecido". Um exemplo de Regra poderia ser descrito como: se o texto do bloco começa com "Parágrafo único" ou "§", então o bloco é classificado como "parágrafo".

Tendo os segmentos parcialmente classificados, o Segmentador agora utiliza as chamadas Heurísticas para aprimorar as categorizações já feitas. Elas utilizam lógicas mais complexas, levando em consideração toda a sequência de blocos para realizar a tarefa. Alguns exemplos de heurísticas são: quando que títulos de normas aparecem mais de uma vez, classificar as ocorrências seguintes como "lixo", já que provavelmente trata-se do cabeçalho do documento; quando um bloco "desconhecido" estiver depois de um título de normativa e antes dos blocos classificados como "preâmbulo", "campo vide" e "considerando", classificá-lo como "ementa".

### Estruturação dos Segmentos

Com os segmentos já classificados, a etapa seguinte consiste em processá-los de forma a reconstruir a estrutura hierárquica das normas. Esta etapa seria similar à análise sintática dos compiladores.

O Estruturador tenta construir tal hierarquia convertendo a sequência de segmentos numa árvore hierárquica com elementos próprios, levando em consideração as classificações e as regras de composição dos vários tipos de elementos. A saber, existem atualmente as seguintes categorias de elementos: Normativa, Ementa, Agrupador, Dispositivo, Pena, Alteração de Ementa, Alteração de Agrupador, Alteração de Dispositivo, Bloco de Alteração, Agrupador para Contexto de Alteração e Dispositivo para Contexto de Alteração.

Cada categoria de elementos mencionada acima pode ser compreendida em dois grupos: os elementos intermediários e os elementos finais. Elementos intermediários, como Normativas, Agrupadores, ou Dispositivos, podem conter outros elementos intermediários ou elementos finais. Já os elementos finais, como Ementas, Pena, Alteração de Agrupador, não podem conter elementos filhos. Tal lógica de elementos intermediários e finais, junto com restrições extras sobre quais categorias de elementos podem ser compostos com quais outras, e o uso da estrutura de dados "stack" (pilha), formam o núcleo lógico do Estruturador.

Para exemplificar o funcionamento do Estruturador, considera-se que já exista na pilha de elementos processados: uma Normativa, um Agrupador de Capítulo, um Agrupador de Sessão, um Dispositivo de Artigo e um Dispositivo de Parágrafo. Os próximos elemento a serem processado serão um Dispositivo de Inciso, um Dispositivo de Parágrafo e um Agrupador de Sessão.

A estrutura atual pode ser visualizada assim:

```
Normativa
└── Agrupador de Capítulo
    └── Agrupador de Sessão
        └── Dispositivo de Artigo
            └── Dispositivo de Parágrafo
```

Ao tentar processar o inciso, o Estruturador observa que o último elemento na pilha é um Parágrafo, que Dispositivos podem ser filhos de outros Dispositivos, e que não existe outro Dispositivo de Inciso atualmente na pilha. Com isso, ele toma a decisão de incluir o inciso como um elemento filho do parágrafo e adiciona esse inciso na pilha. A estrutura resultante é dada abaixo.

```
Normativa
└── Agrupador de Capítulo
    └── Agrupador de Sessão
        └── Dispositivo de Artigo
            └── Dispositivo de Parágrafo
                └── Dispositivo de Inciso
```

No processamento do elemento seguinte, um Dispositivo de Parágrafo, o Estruturador observa uma situação bem similar à anterior, entretanto já existe outro Dispositivo de Parágrafo na pilha. Ele então remove da pilha tanto o Inciso quanto o Parágrafo já existente, e adiciona o parágrafo novo como filho do elemento ainda presente na pilha, o Dispositivo de Artigo, e o adiciona esse novo Parágrafo na pilha.

```
Normativa
└── Agrupador de Capítulo
    └── Agrupador de Sessão
        └── Dispositivo de Artigo
            ├── Dispositivo de Parágrafo
            │   └── Dispositivo de Inciso
            └── Dispositivo de Parágrafo
```

Por fim, para o processamento do Agrupador de Sessão, o Estruturador nota que Agrupadores não podem ser filhos de Dispositivos, e que já existe outro agrupador de Sessão na pilha, então, de forma similar ao passo anterior, ele remove da pilha todos os elementos até chegar no Agrupador de Capítulo, e adiciona o último Agrupador de Sessão na pilha. O resultado é dado abaixo.

```
Normativa
└── Agrupador de Capítulo
    ├── Agrupador de Sessão
    │   └── Dispositivo de Artigo
    │       ├── Dispositivo de Parágrafo
    │       │   └── Dispositivo de Inciso
    │       └── Dispositivo de Parágrafo
    └── Agrupador de Sessão
```

Observa-se que o Estruturador não precisa necessariamente levar em consideração a ordem esperada dos vários tipos de dispositivos (artigo, paragrafo, inciso, item) ou de agrupadores (livro, capítulo, seção), o que tem a vantagem de simplificar o código, não tornar a estruturação rígida, e manter a possibilidade de se representar normas formatadas fora do padrão usual. Além disso, quando um elemento não pode ser inserido na árvore sem violar alguma das regras supracitadas, ele provavelmente se trata de um trecho problemático da norma ou algum artefato do documento, como uma numeração de páginas em um PDF, e pode ser descartado sem grandes perdas.

Para fins de melhoria na qualidade de dados, alguns processamentos extras são feitos. Por exemplo, alguns segmentos descartados sumariamente nesta etapa, como os classificados como "Lixo" ou "Desconhecido". Segmentos dentro de anexos, mesmo que contenham dispositivos legais, atualmente também são descartados, já que necessitariam de uma lógica mais robusta para identificar se eles formam uma norma bem-comportada, a fim de não adicionar ruído no resultado. O Estruturador também tenta fundir os textos presentes em sequências de segmentos de "continuação", e remove os trechos entre parênteses que ocorrem no final dos dispositivos, que ainda são salvos como uma "nota de status" daquele dispositivo. Essas notas tipicamente indicam qual outro normativo alterou aquele trecho.

O resultado da estruturação pode ser salvo num arquivo usando o conhecido formato textual `yaml`, para uma fácil visualização humana e manipulação por máquina. Vide o exemplo abaixo do formato `yaml`.

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

O objetivo inicial do projeto era realizar uma classificação dos artigos de diversas normativas utilizando grandes modelos de linguagem (LLMs), de acordo com a presença ou ausência de algumas dimensões relevantes para o projeto. Porém, ao se observar a dificuldade de isolar os artigos nos mais diversos formatos de arquivos; tratar dispositivos que modificam outras normativas, uma situação bastante presente do corpus das normativas de interesse; e que em alguns casos, utilizar somente o caput do artigo poderia ter muito pouca informação, acreditou-se interessante construir uma solução mais robusta para facilitar o pré processamento das normas.

Vide o exemplo deste artigo:

```
Art. 39. O operador deverá realizar o tratamento segundo as instruções fornecidas pelo controlador, que verificará a observância das próprias instruções e das normas sobre a matéria.
```

Mesmo numa leitura humana, somente o caput da lei trás muito pouca informação sobre o contexto da lei, especialmente quando se está interessado em realizar uma análise textual. O leitor deveria ter conhecimento pretérito de que esse trecho trata de conceitos presentes na Lei Geral de Proteção de Dados Pessoais para realizar uma avaliação adequada. Entretanto, quando se adiciona informações contextuais, como as presentes no exemplo abaixo, esse problema pode ser mitigado: pela ementa da lei, é possível saber que se trata da LGPD, e as denominações do Capítulo e da Seção informam que controladores e operadores são espécies de agentes de tratamento de dados pessoais.

```
LEI Nº 13.709, DE 14 DE AGOSTO DE 2018
Ementa: Lei Geral de Proteção de Dados Pessoais (LGPD).

CAPÍTULO VI - DOS AGENTES DE TRATAMENTO DE DADOS PESSOAIS
Seção I - Do Controlador e do Operador

Art. 39. O operador deverá realizar o tratamento segundo as instruções fornecidas pelo controlador, que verificará a observância das próprias instruções e das normas sobre a matéria.
```

Tendo as normativas estruturadas na forma dada na seção acima "Estruturação dos Segmentos", é possível criar representações textuais com informações arbitrárias de qualquer ponto das normativas. No caso desse projeto, optou-se por usar os artigos como unidade de análise, porém também seria possível utilizar qualquer outra unidade, como agrupamentos inteiros, ou até construir a unidade de observação de forma dinâmica de acordo com o tamanho dos dispositivos.

Neste projeto, utilizou-se o algoritmo clássico de busca em profundidade para localizar os artigos nas normativas já estruturadas. Então, se criou uma representação textual do artigo utilizando toda sua sequência de elementos ascendentes diretos (tipicamente a normativa, junto com sua ementa, e a sequência de agrupadores) e todos os seus elementos descendentes (outros dispositivos, blocos de alteração e seus filhos). O resultado é similar ao exemplo anterior da LGPD.

Tendo a representação textual contextualizada de cada artigo, junto com instruções extras para realizar as classificações, utilizou-se de uma LLM isso, aproveitando a funcionalidade de "decodificação estruturada", que obriga a resposta da LLM ter um formato específico. Os resultados então são salvos num banco de dados durante o processamento para análise posterior.

## Desenvolvimento

Durante o desenvolvimento da solução, houve tentativas de se utilizar LLMs em todo o processamento do corpus normativo, especialmente nas etapas de segmentação e estruturação, porém devido às alucinações sofridas pelo modelo de linguagem, o resultado não foi considerado como confiável e a abordagem foi descontinuada.

LLMs também foram utilizadas para avaliar os resultados das fases de segmentação e estruturação, identificando resultados anômalos. Seu uso se revelou bastante útil em corpus com muitas normativas, ou alguma normativa maior, o que impediria a avaliação humana minuciosa.

Outro aprendizado relevante foi sobre o uso da técnica de "snapshot testing", na qual o resultado atual do processamento é comparado com uma nova versão proposta. Um pequeno utilitário foi feito para avaliar o processo de segmentação, realçando as diferenças entre as versões. Essa é a etapa mais crítica do processamento, pois envolve muitas heurísticas para realizar as classificações dos segmentos, e esses erros podem ser propagados para o estruturador. A técnica se provou de muita valia, pois torna possível realizar melhorias incrementais nos resultados tendo a certeza de que não houve regressões nos demais casos.

## Limitações e trabalhos futuros

Como o projeto tinha inicialmente um escopo muito específico, algumas normativas importantes do ordenamento jurídico brasileiro ainda não foram testadas. Acredita-se que o sistema funcione bem para leis mais recentes, especialmente após a [lei complementar 95 de 1998](https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp95.htm), por serem mais padronizadas e seguirem uma técnica de escrita legislativa mais restrita. Normas mais antigas como o Decreto-Lei 200 ainda funcionam, mas apresentam alguns problemas.

Este projeto visa ser utilizado também para estudar normativas secundárias, que podem ser materializadas das mais diversas formas, especialmente como PDFs. Entretanto, o formato foi pensado para publicações, e não edição ou leitura do texto subjacente por máquina. Um esforço foi feito para se concatenar as linhas contíguas que parem ser continuações, remover artefatos como numeração de página, cabeçalhos e epílogos típicos, entretanto esse processamento pode ser problemático. Textos de normativas secundárias diversas podem ser incompatíveis com algumas das heurísticas utilizadas atualmente. Por exemplo, uma resolução de um órgão colegiado feita pelo SEI e publicada em PDF poderá ter uma estrutura no preambulo muito diferente da que geralmente se usa em leis e decretos. Como as heurísticas foram feitas baseando-se principalmente nesses casos, elas podem não identificar as âncoras textuais necessárias, como palavras-chave, no texto da mencionada resolução e sua estruturação ficar prejudicada em algum ponto.

O esquema de identificação de normas revogadas ainda é precário, se baseando somente no fato do texto original estar tachado ou não, por meio de uma característica simplória do HTML original. Então, essa marcação não deve ser levada em consideração por enquanto.

A identificação de ementas e preâmbulos é um ponto fraco. Não existem palavras-chave claras sempre, ou uma posição específica no texto para ajudar a ancorar sua identificação. Seria necessário realizar um julgamento semântico dos textos para aumentar a qualidade dessa seleção.

O código atualmente se baseia somente em heurísticas determinísticas para fazer seu processamento, o que lhe garante um alto grau de reprodutibilidade e interpretabilidade de seus resultados, entretanto pode dificultar sua capacidade de generalização para casos mais adversos, como das supramencionadas identificações de ementas e preâmbulos. O uso de técnicas probabilísticas como aprendizado de máquina ou modelos de linguagem poderiam resolver melhor esses casos difíceis, ao custo talvez piorar a reprodutibilidade e interpretabilidade, além de talvez requerer mais poder computacional do usuário final. Uma abordagem híbrida pode ser salutar.

Outro ponto de atenção do módulo Python é que se observa que os componentes de segmentação e estruturação estão com lógicas complexas e muito acopladas internamente, o que dificulta sua compreensão e manutenção. Uma readequação da arquitetura, criando abstrações para esses componentes a fim de simplificá-los, pode ser necessária para facilitar sua manutenção e extensibilidade num horizonte de tempo maior.

O módulo Python foi majoritariamente escrito de forma manual pelo autor. O uso de LLMs no desenvolvimento foi esporádico, auxiliando na construção de alguns trechos e na escrita dos testes automatizados. Logo, tais trechos devem ser revistos no futuro, mas o risco de problemas sistêmicos ou [débito cognitivo](https://www.thoughtworks.com/en-br/radar/techniques/codebase-cognitive-debt) em relação ao uso de LLMs é baixo.

Como ideias de contribuições futuras, observa-se que a norma estruturada poderia ser enriquecida com informações sobre as referências que um dispositivo faz para outro dispositivo ou normativa, como em "§ 2º Os contratos e convênios de que trata o § 1º deste artigo deverão ser comunicados à autoridade nacional". Atualmente, dispositivos que possuem links são marcados como tal num atributo específico para isso, sendo uma versão inicial dessa funcionalidade. Tal informação seria interessante para análises gráficas das matérias ou até para aprimorar uma representação textual dos dispositivos para um processamento posterior, aumentando o contexto fornecido com o próprio corpo do § 1º, como no caso acima.

A fim de realizar a proposta acima, ainda é necessário criar um sistema de identificação dos dispositivos e das próprias normas, criando uma identidade única para ambos. Além disso, precisa-se atribuir tal identidade para cada referência feita pelos dispositivos, seja ela interna a própria norma ou externa.

- Leitura do Anexo
- Heurística de qualidade de norma.
