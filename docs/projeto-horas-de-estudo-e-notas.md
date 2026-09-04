# Projeto de Dados: Relação entre Horas de Estudo e Notas

> Documento de planejamento do projeto acadêmico. Reúne problema, metodologia, instrumentos
> de coleta, fórmulas, prompts de IA e a estrutura do relatório final.

---

## Sumário

| # | Seção |
|---|-------|
| 1 | [Tema](#1-tema) |
| 2 | [Problema](#2-problema) |
| 3 | [Objetivo](#3-objetivo) |
| 4 | [Pergunta de pesquisa](#4-pergunta-de-pesquisa) |
| 5 | [Hipótese inicial](#5-hipótese-inicial) |
| 6 | [Dados necessários](#6-dados-necessários) |
| 7 | [Fonte dos dados](#7-fonte-dos-dados) |
| 8 | [Questionário sugerido](#8-questionário-sugerido) |
| 9 | [Aplicação de tecnologia e IA](#9-aplicação-de-tecnologia-e-ia) |
| 10 | [Fluxo de trabalho](#10-fluxo-de-trabalho) |
| 11 | [Organização da planilha](#11-organização-da-planilha) |
| 12 | [Gráficos recomendados](#12-gráficos-recomendados) |
| 13 | [Prompts para IA](#13-prompts-para-ia) |
| 14 | [Análise e interpretação](#14-análise-e-interpretação) |
| 15 | [Limitações do projeto](#15-limitações-do-projeto) |
| 16 | [Resultado esperado](#16-resultado-esperado) |
| 17 | [Estrutura sugerida do relatório](#17-estrutura-sugerida-do-relatório) |
| 18 | [Modelo de conclusão preenchível](#18-modelo-de-conclusão-preenchível) |
|  | [Resumo do projeto](#resumo-do-projeto) |

---

## 1. Tema

Hábitos de estudo e desempenho escolar. O projeto investiga se o tempo dedicado ao estudo
fora do horário de aula está associado às notas obtidas pelos alunos.

## 2. Problema

Existe relação entre a quantidade de horas que os alunos estudam por semana e suas notas
médias?

## 3. Objetivo

Analisar se alunos que estudam mais horas por semana tendem a obter médias maiores,
utilizando coleta digital, planilha automatizada, gráficos e apoio de IA para organizar e
interpretar os dados.

### Objetivos específicos

1. Coletar, de forma anônima e voluntária, dados sobre horas de estudo semanal e média
   escolar mais recente.
2. Organizar as respostas em uma planilha estruturada, com limpeza e validação dos campos
   numéricos.
3. Agrupar os participantes em faixas de horas de estudo e calcular a média de notas de
   cada faixa.
4. Produzir gráficos que permitam visualizar a relação entre as duas variáveis.
5. Redigir um relatório que descreva os padrões observados, reconhecendo as limitações da
   pesquisa e sem afirmar causalidade.

## 4. Pergunta de pesquisa

Alunos que estudam mais horas por semana apresentam, em média, notas maiores do que alunos
que estudam menos horas?

## 5. Hipótese inicial

Espera-se encontrar uma associação positiva entre horas de estudo semanal e média escolar,
ou seja, que as faixas com mais horas de estudo apresentem médias de notas mais altas.

A hipótese pode ser confirmada, parcialmente confirmada ou não confirmada pelos dados. Em
qualquer um dos casos o resultado é válido, e a conclusão deve descrever o que foi
observado, não o que se esperava encontrar.

---

## 6. Dados necessários

| Campo | Tipo de dado | Exemplo | Finalidade |
|-------|--------------|---------|------------|
| Horas de estudo por semana | Número | 5 | Variável principal |
| Média mais recente | Número de 0 a 10 | 8,2 | Indicador de desempenho |
| Série/período | Categoria | 2º ano | Comparar perfis, se necessário |
| Frequência de exercícios extras | Categoria | Frequentemente | Variável complementar |

### Dados que não devem ser coletados

Não coletar nome, matrícula, e-mail, telefone, endereço, CPF, boletim, senha ou qualquer
dado que permita identificar o participante. A pesquisa pode ser realizada com respostas
anônimas.

---

## 7. Fonte dos dados

Os dados serão obtidos por meio de um questionário digital respondido voluntariamente por
alunos da turma ou da instituição.

- **Ferramenta de coleta:** Google Forms ou Microsoft Forms.
- **Armazenamento:** Google Sheets ou Excel Online.
- **Público:** alunos convidados pelo grupo.
- **Meta mínima sugerida:** 20 respostas. Quanto maior o número de respostas, melhor a
  representação do grupo pesquisado.

---

## 8. Questionário sugerido

Crie um formulário com as perguntas abaixo. Mantenha-o curto para aumentar a chance de
resposta.

**1. Quantas horas, em média, você estuda por semana fora do horário de aula?**
- Tipo: resposta numérica.
- Instrução: informe apenas um número. Exemplo: 5.

**2. Qual foi sua média geral mais recente?**
- Tipo: resposta numérica.
- Instrução: informe uma nota de 0 a 10. Exemplo: 7,5.

**3. Qual é a sua série/período?**
- Tipo: múltipla escolha ou lista.
- Opções: adaptar à realidade da turma.

**4. Com que frequência você faz exercícios, revisões ou atividades extras além das aulas?**
- Tipo: múltipla escolha.
- Opções: Nunca; Raramente; Às vezes; Frequentemente; Sempre.

### Texto de abertura para o formulário

> Este questionário faz parte de um projeto acadêmico sobre hábitos de estudo e desempenho
> escolar. A participação é voluntária e anônima. Não informe seu nome nem outros dados
> pessoais. As respostas serão utilizadas somente de forma agregada para gerar tabelas,
> gráficos e conclusões do trabalho.

---

## 9. Aplicação de tecnologia e IA

A tecnologia será usada para reduzir tarefas repetitivas, acelerar a análise e melhorar a
apresentação dos resultados. A decisão final sobre os dados e as conclusões continuará
sendo do grupo.

| Etapa | Ferramenta | Aplicação | Benefício |
|-------|------------|-----------|-----------|
| Coleta | Google Forms / Microsoft Forms | Aplicar questionário por link | Evita anotações e digitação manual |
| Armazenamento | Google Sheets / Excel | Registrar cada resposta em uma linha | Organiza dados automaticamente |
| Limpeza | Planilha e IA | Identificar células vazias, números fora do padrão e duplicidades | Reduz erros de organização |
| Análise | Google Sheets / Excel / IA | Calcular médias, comparar grupos e identificar tendências | Acelera cálculos e leitura inicial |
| Visualização | Google Sheets / Excel | Gerar gráficos | Facilita a comunicação dos resultados |
| Redação | IA generativa | Criar rascunho da metodologia e dos resultados a partir de dados revisados | Economiza tempo de escrita |
| Apresentação | Google Slides / PowerPoint / IA | Sugerir estrutura de slides e roteiro | Padroniza a entrega |

### Regras para uso responsável da IA

- Não enviar nomes, e-mails, matrículas ou outros dados pessoais para ferramentas de IA.
- Enviar somente uma tabela anônima, preferencialmente sem identificadores.
- Conferir todas as médias, números e conclusões sugeridas pela IA.
- Não copiar uma resposta da IA sem verificar se ela corresponde aos dados coletados.
- Informar no relatório que a IA foi usada como apoio à organização, análise inicial e
  redação, quando isso for solicitado pelo professor.
- Não afirmar que uma variável causa a outra apenas porque os dados mostram uma tendência.

---

## 10. Fluxo de trabalho

1. O grupo cria o formulário com as quatro perguntas propostas.
2. O grupo divulga o link para os participantes e estabelece um prazo de resposta.
3. As respostas são enviadas automaticamente para uma planilha.
4. O grupo confere se os campos numéricos estão corretos e remove respostas incompletas ou
   claramente inválidas.
5. O grupo cria uma coluna de faixas de horas de estudo.
6. A planilha calcula médias e quantidades por faixa.
7. O grupo gera gráficos e revisa os resultados.
8. Uma IA pode produzir um resumo inicial com base na tabela anônima e nos cálculos já
   conferidos.
9. O grupo revisa o texto, escreve a conclusão e prepara os slides.

---

## 11. Organização da planilha

### Estrutura recomendada

| Coluna | Nome |
|--------|------|
| A | Data/hora da resposta |
| B | Horas de estudo por semana |
| C | Média mais recente |
| D | Série/período |
| E | Frequência de exercícios extras |
| F | Faixa de horas de estudo |

### Fórmula para criar a faixa de horas

No Google Sheets ou Excel, considerando que as horas estejam na célula B2, use a fórmula
abaixo na coluna F:

```
=SE(B2<=2;"0 a 2 horas";SE(B2<=5;"3 a 5 horas";SE(B2<=8;"6 a 8 horas";"Mais de 8 horas")))
```

> Se a planilha estiver configurada em inglês, a função pode aparecer como `IF` em vez de
> `SE`, e o separador pode ser vírgula em vez de ponto e vírgula.

### Fórmulas úteis

Considerando horas em `B2:B100` e médias em `C2:C100`:

```
=MÉDIA(B2:B100)
```
Calcula a média de horas estudadas por semana.

```
=MÉDIA(C2:C100)
```
Calcula a média geral das notas.

```
=CONT.NÚM(B2:B100)
```
Conta quantas respostas numéricas válidas foram registradas para horas de estudo.

```
=MÉDIASE(F2:F100;"0 a 2 horas";C2:C100)
```
Calcula a média das notas do grupo que estuda de 0 a 2 horas por semana. Repita a fórmula
para as demais faixas.

```
=CONT.SE(F2:F100;"0 a 2 horas")
```
Conta quantos alunos pertencem à faixa de 0 a 2 horas por semana.

---

## 12. Gráficos recomendados

### Gráfico 1, Dispersão

- **Eixo X:** horas de estudo por semana.
- **Eixo Y:** média mais recente.
- **Finalidade:** observar se as notas parecem aumentar, diminuir ou não variar conforme
  aumentam as horas de estudo.

### Gráfico 2, Barras

- **Eixo X:** faixas de horas de estudo.
- **Eixo Y:** média das notas em cada faixa.
- **Finalidade:** comparar de forma simples o desempenho médio de cada grupo.

### Gráfico 3, Barras (opcional)

- **Eixo X:** frequência de exercícios extras.
- **Eixo Y:** média das notas.
- **Finalidade:** verificar se essa variável complementar parece ter alguma relação com o
  desempenho.

---

## 13. Prompts para IA

> Copie e cole somente dados anônimos e já revisados.

### Prompt para limpeza dos dados

```
Você é um assistente de análise de dados. Analise a tabela anônima abaixo, que contém
horas de estudo semanal e médias escolares.

1. Identifique valores ausentes, duplicados ou possivelmente inválidos.
2. Não altere os dados sem explicar a sugestão.
3. Liste quais registros precisam de revisão e por quê.
4. Não invente valores.

[TABELA ANÔNIMA AQUI]
```

### Prompt para análise exploratória

```
Analise a tabela anônima abaixo sobre horas de estudo semanal e médias escolares.

1. Calcule a média de horas de estudo e a média geral das notas.
2. Compare a média das notas nas faixas: 0 a 2 horas, 3 a 5 horas, 6 a 8 horas e mais
   de 8 horas.
3. Descreva tendências aparentes, sem afirmar causalidade.
4. Cite possíveis fatores que podem influenciar as notas além das horas de estudo.
5. Sugira dois gráficos adequados.
6. Não invente números: use exclusivamente a tabela fornecida.

[TABELA ANÔNIMA AQUI]
```

### Prompt para redigir resultados

```
Com base exclusivamente nos resultados abaixo, escreva uma seção de resultados para um
relatório acadêmico.

Inclua: tamanho da amostra, média de horas de estudo, média das notas, comparação por
faixa de horas de estudo e descrição dos gráficos.

Não use palavras que indiquem causalidade, como "provou" ou "causou". Use expressões
como "os dados sugerem", "observou-se" e "no grupo pesquisado".

[RESULTADOS CONFERIDOS AQUI]
```

---

## 14. Análise e interpretação

### O que observar

- A média de nota cresce conforme aumentam as faixas de horas de estudo?
- Há muitas respostas concentradas em uma única faixa?
- Existem valores muito fora do padrão, como 0 horas com nota 10 ou 50 horas semanais?
  Eles podem ser reais, mas devem ser conferidos.
- A frequência de exercícios extras parece acompanhar notas mais altas?
- A quantidade de respostas é suficiente para sustentar uma conclusão apenas sobre o grupo
  pesquisado?

### Como escrever uma conclusão correta

Use linguagem cuidadosa. Exemplos adequados:

- "Nos dados coletados, os alunos que relataram estudar mais horas apresentaram, em média,
  notas maiores."
- "Os resultados sugerem uma associação entre tempo de estudo e média escolar no grupo
  pesquisado."
- "A pesquisa não permite afirmar que mais horas de estudo, isoladamente, causam notas mais
  altas, pois outros fatores podem influenciar o resultado."

Evite frases como:

- "Estudar mais causa notas maiores."
- "A pesquisa provou que quem estuda mais é mais inteligente."
- "Todos os alunos que estudam pouco têm notas baixas."

---

## 15. Limitações do projeto

O trabalho deve reconhecer suas limitações:

- As notas e horas estudadas são informadas pelos participantes e podem conter imprecisões.
- A amostra pode ser pequena e representar apenas uma turma ou grupo específico.
- Outros fatores influenciam as notas: frequência escolar, dificuldades em disciplinas,
  qualidade do sono, rotina, apoio familiar, método de estudo e acesso a recursos.
- A análise identifica tendências e associações; ela não demonstra causa e efeito.

---

## 16. Resultado esperado

Ao final, o grupo deverá entregar:

- Um formulário digital utilizado para a coleta.
- Uma planilha anônima e organizada.
- Uma tabela-resumo com médias e quantidade de respostas por faixa de estudo.
- Pelo menos dois gráficos.
- Um relatório curto com problema, objetivo, metodologia, resultados, interpretação,
  limitações e conclusão.
- Uma apresentação com os principais achados.

---

## 17. Estrutura sugerida do relatório

### Introdução

Explique que hábitos de estudo podem estar relacionados ao desempenho escolar e apresente a
pergunta de pesquisa.

### Metodologia

Informe que foi aplicado um questionário digital anônimo. Descreva o público participante,
a quantidade de respostas, as variáveis coletadas e as ferramentas usadas para organizar e
analisar os dados.

### Resultados

Apresente as médias, a tabela por faixa de horas e os gráficos. Descreva apenas o que os
dados mostram.

### Discussão

Interprete os padrões observados, mencione possíveis explicações e apresente as limitações
da pesquisa.

### Conclusão

Responda à pergunta de pesquisa usando uma frase cuidadosa, baseada nos resultados obtidos.

---

## 18. Modelo de conclusão preenchível

> Foram analisadas **[N]** respostas anônimas. A média de horas de estudo semanal foi de
> **[X]** horas e a média geral das notas foi de **[Y]**. Os dados mostraram que o grupo
> que estudava **[FAIXA]** apresentou a maior média de notas, de **[NOTA]**. Assim, para o
> grupo pesquisado, observou-se **[uma associação positiva / ausência de associação clara /
> uma tendência fraca]** entre horas de estudo e médias escolares. Entretanto, os
> resultados não permitem afirmar uma relação de causa e efeito, porque outros fatores
> também podem influenciar o desempenho acadêmico.

---

## Resumo do projeto

**Problema:** Existe relação entre a quantidade de horas que os alunos estudam por semana e
suas notas médias?

**Objetivo:** Analisar se alunos que estudam mais horas por semana tendem a obter médias
maiores, utilizando coleta digital, planilha automatizada, gráficos e apoio de IA para
organizar e interpretar os dados.

**Dados:** Horas de estudo por semana, média escolar mais recente, série/período e
frequência de exercícios extras.

**Fonte:** Questionário digital anônimo respondido por alunos e armazenado em uma planilha
online.

**Resultado:** Uma planilha organizada, tabela-resumo, gráficos e um relatório explicando
se os dados sugerem ou não uma associação entre horas de estudo e desempenho acadêmico.
