# Projeto de Dados: Relação entre Tempo Semanal de Estudo e Desempenho Escolar

> Plano atualizado para utilizar a base pública real Student Performance, da UCI.
> A coleta por formulário foi substituída pela aquisição de dados secundários.
> A implementação está em [Coleta, Tratamento e ETL](coleta-tratamento-etl.md).

## 1. Tema

Hábitos de estudo e desempenho escolar. Investigar como as notas finais de uma disciplina
variam entre categorias de tempo semanal de estudo em uma base pública de duas escolas
de ensino secundário de Portugal.

## 2. Problema

Existe associação entre a faixa de tempo semanal de estudo e a nota final da disciplina?

## 3. Objetivo

Comparar as notas finais entre as faixas de estudo da base UCI, com ETL reproduzível,
planilhas, gráficos e apoio de IA na redação a partir dos resultados conferidos.

Objetivos específicos:

1. Obter os CSVs oficiais e registrar fonte, atribuição, data de obtenção e hashes.
2. Validar a estrutura e os domínios das variáveis utilizadas, preservando os originais.
3. Preparar uma base com categorias de estudo e notas por disciplina.
4. Calcular quantidades e médias por faixa, com Português como análise principal e
   Matemática como comparação separada.
5. Produzir gráficos e redigir conclusões que reconheçam limites e não afirmem causalidade.

## 4. Pergunta de pesquisa

Na base Student Performance, os alunos nas faixas de maior tempo semanal de estudo
apresentam, em média, notas finais maiores em Português?

A mesma pergunta pode ser investigada separadamente em Matemática. Não se combina o
desempenho das duas disciplinas numa média geral por aluno.

## 5. Hipótese inicial

Espera-se uma associação positiva entre as categorias de estudo e a nota final. A hipótese
é uma expectativa, não um resultado. A comparação pode mostrar crescimento irregular,
diferenças pequenas ou ausência de um padrão claro.

## 6. Dados necessários

| Variável | Tipo e significado | Uso |
|---|---|---|
| `studytime` | Categoria ordinal de 1 a 4, tempo semanal de estudo | Variável principal |
| `G3` | Nota final da disciplina, inteiro de 0 a 20 | Indicador de desempenho |
| `G1`, `G2` | Notas do primeiro e segundo períodos de avaliação, de 0 a 20 | Contexto complementar |
| `disciplina` | Português ou Matemática, derivada do arquivo de origem | Separar análises |
| `faixa_estudo` | Rótulo derivado de `studytime` | Apresentação |
| `nota_final_0_10` | `G3 / 2`, decimal | Escala opcional, explicitamente convertida |

Os períodos de avaliação de G1/G2 não são série ou semestre do curso. A base não fornece
as horas exatas, a média geral escolar ou a frequência de exercícios extras do formulário
anterior. Não preencher essas variáveis com suposições.

## 7. Fonte dos dados

[Student Performance — UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/320/student+performance).
Criador: Paulo Cortez. A fonte documenta aquisição por questionários e registros escolares
em duas escolas portuguesas, com arquivos de Português e Matemática.

- `student-por.csv`: 649 registros, análise principal.
- `student-mat.csv`: 395 registros, análise complementar.
- Ambos possuem 33 colunas na exportação original.
- Há alunos presentes nos dois arquivos, conforme `student.txt`. A unidade da base
  consolidada é **aluno por disciplina**; 1.044 linhas não são 1.044 alunos únicos.
- Licença indicada pela UCI: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/),
  com a atribuição em [data/README.md](../data/README.md).

Este trabalho utiliza dados secundários. O grupo não aplicou o questionário original
nem coletou respostas de alunos da FATEC.

## 8. Instrumento de aquisição e categorias da fonte

O instrumento operacional é o coletor `scripts/coletar_uci.py`, que baixa o ZIP oficial,
extrai os CSVs e o dicionário e registra um manifesto. Não há formulário a aplicar nesta
versão do projeto.

| Código `studytime` | Rótulo da faixa |
|---|---|
| 1 | Menos de 2 horas |
| 2 | 2 a 5 horas |
| 3 | 5 a 10 horas |
| 4 | Mais de 10 horas |

Preservar as categorias recebidas. A redação da fonte compartilha o limite de 5 nas
faixas intermediárias, mas cada registro já possui um código único. Não é necessário
reclassificar horários individuais nem decidir limites que não estão disponíveis.

## 9. Aplicação de tecnologia e IA

| Etapa | Ferramenta | Aplicação |
|---|---|---|
| Aquisição | Python / HTTPS | Baixar o pacote oficial e registrar procedência |
| Tratamento | Python, biblioteca padrão | Validar dados e transformar categorias |
| Armazenamento | CSV e JSON | Preservar fontes e separar produtos do ETL |
| Análise | Excel / Google Sheets | Comparar quantidades e médias por faixa e disciplina |
| Visualização | Excel / Google Sheets | Barras e distribuição das notas por categoria |
| Redação | IA generativa | Apoiar texto a partir de resumos revisados |
| Apresentação | PowerPoint / Google Slides | Comunicar os resultados |

Enviar à IA preferencialmente tabelas agregadas. Não enviar os atributos demográficos,
familiares ou de saúde dos originais. Conferir cálculos e conclusões, informar o uso de IA
quando solicitado e não atribuir efeitos causais ao tempo de estudo.

## 10. Fluxo de trabalho

1. Baixar e registrar os arquivos oficiais com `python scripts/coletar_uci.py`.
2. Gerar a base e os resumos com `python scripts/etl.py`.
3. Conferir o relatório de qualidade e eventuais ocorrências.
4. Importar os CSVs em Excel/Sheets com delimitador `;` e localidade brasileira.
5. Filtrar Português para a análise principal; Matemática é investigada em separado.
6. Comparar as quatro faixas e avaliar quantidades e distribuição das notas.
7. Produzir os gráficos, revisar o texto e preparar relatório e apresentação.

## 11. Organização da planilha

O CSV tratado usa a seguinte ordem:

| Coluna | Campo |
|---|---|
| A | `disciplina` |
| B | `registro_origem` |
| C | `studytime` |
| D | `faixa_estudo` |
| E | `G1` |
| F | `G2` |
| G | `G3` |
| H | `nota_final_0_10` |
| I | `sinalizacoes` |

A faixa já é criada pelo ETL. Se for necessário reproduzir a transformação para registros
válidos, usar `=ESCOLHER(C2;"Menos de 2 horas";"2 a 5 horas";"5 a 10 horas";"Mais de 10 horas")`.
A escala opcional na coluna H corresponde a `=G2/2`.

Exemplos para Português, com intervalo até a linha 2000:

```text
=CONT.SES($A$2:$A$2000;"Português";$C$2:$C$2000;1)
=MÉDIASES($G$2:$G$2000;$A$2:$A$2000;"Português";$C$2:$C$2000;1)
=MÉDIASE($A$2:$A$2000;"Português";$G$2:$G$2000)
```

Os dois primeiros exemplos contam registros e calculam a nota final média na primeira
faixa. Repetir com códigos 2, 3 e 4. O último calcula a nota final média da disciplina.
Conferir se há registros antes de calcular a média de uma categoria vazia. Para Matemática,
trocar o filtro de disciplina. Não calcular “média de horas” a partir dos códigos de C.
Funções e separadores podem variar conforme idioma/configuração da planilha.

## 12. Gráficos recomendados

1. **Barras:** quatro faixas no eixo X, média de G3 na escala de 0 a 20 no eixo Y.
   Exibir ou informar a quantidade de registros por faixa. Português é o gráfico principal.
2. **Boxplot das notas por faixa:** comparar dispersão, mediana e extremos de G3 nas
   quatro categorias de Português. Se a ferramenta não oferecer boxplot, usar pontos de
   nota por categoria, com eixo X explicitamente categórico e sobreposição indicada.
3. **Barras de Matemática, opcional:** repetir a comparação em figura separada.

Não usar dispersão com “horas exatas” no eixo X: a fonte não possui essa variável.
Não apresentar 1, 2, 3 e 4 como horas. Evitar regressão que trate os códigos como
intervalos iguais de tempo. Os gráficos fazem parte da próxima etapa de análise.

## 13. Prompts para IA

### Apoio à revisão

```text
Revise os resumos e o relatório de qualidade da base UCI Student Performance.
Confronte contagens por disciplina e faixa. G3 vai de 0 a 20; zero é válido.
studytime é ordinal, com faixas originais, e não representa horas exatas.
Não remova registros iguais nas variáveis analíticas nem invente valores ausentes.
Liste problemas que precisem de verificação. Não tente identificar alunos.
[RESUMOS E QUALIDADE CONFERIDOS]
```

### Apoio à análise e redação

```text
Com base exclusivamente nos resumos abaixo, descreva as notas finais de Português
por faixa de estudo semanal. Informe as quantidades e a escala original de 0 a 20.
Compare as faixas sem presumir um crescimento constante. Matemática, se fornecida,
deve ser descrita separadamente. Há alunos nos dois arquivos, portanto não some
as linhas como pessoas distintas. Não calcule horas médias a partir de studytime.
Não afirme causalidade e não generalize para alunos da FATEC.
[RESULTADOS CONFERIDOS]
```

## 14. Análise e interpretação

Observar o tamanho desigual das faixas, a variação das notas dentro dos grupos e se
a maior faixa realmente apresenta a maior média. A média sozinha não descreve toda
a distribuição. Notas G3=0 permanecem na comparação; eventual análise de sensibilidade
deve ser adicional, explícita e justificada, sem substituir a análise principal.

Usar expressões como “na base analisada” e “observou-se diferença de médias”. Os dados
são observacionais: outros fatores podem explicar diferenças entre as faixas.

## 15. Limitações do projeto

- A população é de duas escolas portuguesas, não da FATEC ou do Brasil.
- Os dados são históricos; a referência de 2008 não indica a data do download.
- O tempo de estudo é categórico e pode conter imprecisão de autorrelato.
- G3 é a nota final de uma disciplina, não a média geral do aluno.
- Categorias têm tamanhos diferentes e não representam distâncias iguais em horas.
- Há sobreposição de alunos entre disciplinas; não se assume independência entre arquivos.
- A validação abrange somente a estrutura e as quatro variáveis analíticas; não declara
  que todos os demais atributos da fonte passaram por auditoria.
- Diferenças descritivas não demonstram causalidade nem significância estatística.

## 16. Resultado esperado

- Fonte pública citada e aquisição reproduzível.
- Base tratada minimizada e relatório de qualidade.
- Resumos por faixa e disciplina.
- Pelo menos dois gráficos pertinentes às categorias disponíveis.
- Relatório com introdução, metodologia, resultados, discussão, limites e conclusão.
- Apresentação dos principais achados.

A obtenção, o tratamento e a preparação da base já foram executados; gráficos e
interpretação detalhada pertencem às etapas posteriores.

## 17. Estrutura sugerida do relatório

**Introdução:** apresentar a associação entre estudo e desempenho como pergunta.

**Metodologia:** informar uso de dados secundários UCI, referência e licença, escolha de
Português, separação de Matemática, variáveis, categorias, escala e políticas do ETL.
Não escrever que o grupo aplicou um formulário.

**Resultados:** apresentar quantidades, notas médias por faixa e gráficos, com escala e
disciplina identificadas.

**Discussão:** avaliar padrões observados e possíveis explicações, sem inferir horas exatas.

**Conclusão:** responder à pergunta para a população da fonte, sem afirmar causalidade.

## 18. Modelo de conclusão preenchível

> Foram analisados [N] registros de Português da base pública Student Performance/UCI.
> A nota final média foi [Y], na escala de 0 a 20. A faixa [FAIXA] apresentou a maior
> nota final média, de [NOTA]. A comparação entre as categorias indicou [DESCREVER O
> PADRÃO OBSERVADO], considerando seus diferentes tamanhos. O tempo de estudo foi
> registrado em faixas, sem horas exatas. Os resultados dizem respeito às escolas da
> fonte e não permitem concluir que estudar por mais tempo causa notas maiores.

## Resumo do projeto

**Pergunta:** como G3 varia entre as faixas de estudo semanal em Português?

**Fonte:** dados reais secundários Student Performance/UCI, referência Cortez (2008),
[DOI: 10.24432/C5TG7T](https://doi.org/10.24432/C5TG7T).

**Método:** aquisição oficial, validação, transformação categórica e comparação descritiva
por disciplina, com preservação dos originais e minimização de atributos.

**Base preparada:** 649 registros de Português e 395 de Matemática, sem exclusões no
processamento realizado. Não há contagem consolidada de alunos únicos.
