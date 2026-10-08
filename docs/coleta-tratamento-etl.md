# Coleta, Tratamento e ETL

## Objetivo e execução realizada

Preparar uma base real para analisar a relação entre **faixa de estudo semanal** e
**nota final por disciplina**, utilizando dados secundários públicos da
[Student Performance/UCI](https://archive.ics.uci.edu/dataset/320/student+performance).

A coleta oficial e o ETL foram reexecutados e verificados em **08/10/2026**, confirmando
os resultados da execução anterior de 17/09/2026. O projeto passou da coleta
por questionário próprio para a aquisição de dados secundários. Os dados escolares não
foram coletados pelo grupo e não representam alunos da FATEC.

**Resultado do processamento:** 649 registros válidos de Português e 395 de Matemática,
sem exclusões ou alertas de linha completa repetida. Os arquivos brutos foram preservados.
São 1.044 observações de aluno por disciplina, com alunos compartilhados entre arquivos,
e não 1.044 pessoas diferentes. Português é a análise principal.

## 1. Obtenção dos dados — Extract

Fonte: Cortez, P. (2008). *Student Performance [Dataset]*, UCI Machine Learning Repository,
[DOI: 10.24432/C5TG7T](https://doi.org/10.24432/C5TG7T).
O repositório documenta notas e atributos escolares obtidos em duas escolas de Portugal
por questionários e registros escolares. A referência de 2008 não é a data de aquisição
local dos arquivos.

O coletor [scripts/coletar_uci.py](../scripts/coletar_uci.py):

1. Baixa o [pacote HTTPS oficial](https://archive.ics.uci.edu/static/public/320/student%2Bperformance.zip).
2. Abre `student.zip` dentro do pacote, ignorando a versão `.student.zip_old`.
3. Extrai somente `student-por.csv`, `student-mat.csv` e o dicionário `student.txt`, sem
   executar arquivos e sem utilizar caminhos arbitrários do ZIP.
4. Salva os bytes originais em `data/raw/uci/` e registra fonte, download, referência,
   licença, data de obtenção e SHA-256 em `manifesto.json`.
5. Interrompe a aquisição se já houver um arquivo bruto diferente no destino; nesse
   caso, uma nova versão da fonte deve ser guardada em outra pasta.

O coletor foi verificado com download direto da UCI, e o manifesto atual registra
`download_oficial_https`. A opção offline `--arquivo` registra `importacao_de_pacote_local`
e preserva a referência oficial como procedência esperada do pacote. O SHA-256 obtido foi
`82ae9d66437b9808df42e8c89d2bb179c46e9cfbcf06f38abc1d20b3b747e177`.

As exportações possuem 33 colunas, delimitador `;` e campos com aspas. O ETL verifica
o cabeçalho oficial e a estrutura dos registros, mas carrega somente as variáveis de estudo
e notas. Os atributos pessoais/contextuais dos originais ficam fora da base analítica.

## 2. Dicionário da base tratada

| Campo | Tipo | Significado e validação |
|---|---|---|
| `disciplina` | Categoria | Português ou Matemática, derivada do arquivo |
| `registro_origem` | Inteiro | Posição da observação no CSV, começando em 1 após o cabeçalho; não é matrícula |
| `studytime` | Inteiro ordinal | Código de 1 a 4; não é quantidade de horas |
| `faixa_estudo` | Categoria | Rótulo original traduzido, derivado do código |
| `G1` | Inteiro | Nota do primeiro período de avaliação, 0 a 20 |
| `G2` | Inteiro | Nota do segundo período de avaliação, 0 a 20 |
| `G3` | Inteiro | Nota final da disciplina, 0 a 20; variável de desempenho principal |
| `nota_final_0_10` | Decimal | Conversão opcional explícita: `G3 / 2` |
| `sinalizacoes` | Texto controlado | Aviso de linha completa repetida, quando houver |

O número de origem é único somente **dentro da disciplina**. Não ligar linhas de Português
e Matemática por esse número. A primeira observação costuma corresponder à linha 2 da
planilha; linhas vazias e campos multilinha podem alterar essa correspondência física.

| Código `studytime` | Rótulo preservado |
|---|---|
| 1 | Menos de 2 horas |
| 2 | 2 a 5 horas |
| 3 | 5 a 10 horas |
| 4 | Mais de 10 horas |

A fonte já atribui uma categoria única a cada registro. O texto compartilha o limite de
5 nas categorias intermediárias; o ETL mantém o código fornecido e não reclassifica dados
que não possui. Não aplicar as faixas 0–2, 3–5, 6–8 e mais de 8 do questionário anterior.

G3 não é média geral escolar. G1/G2 não informam série/período acadêmico. Frequência de
exercícios extras e horas exatas não são preenchidas, pois não existem no contrato desta
base. A média dos códigos `studytime` não é uma média de horas.

## 3. Limpeza e validação — Transform

| Situação | Política |
|---|---|
| Cabeçalho diferente das 33 variáveis oficiais, coluna extra ou repetida | Interromper antes de escrever saídas |
| Um dos dois CSVs ausente ou CSV ilegível | Interromper antes de escrever saídas |
| Espaços externos em `studytime`, G1, G2 ou G3 | Remover na interpretação, mantendo o bruto intacto |
| Variável analítica ausente | Excluir a observação da base e registrar o motivo, sem imputar |
| Código `studytime` fora de 1 a 4 | Excluir e registrar o motivo |
| G1, G2 ou G3 fora de 0 a 20 | Excluir e registrar o motivo |
| Decimal, texto, infinito, `NaN`, unidades ou notação científica em campos inteiros | Excluir e registrar o motivo |
| Registro com quantidade de campos diferente do cabeçalho | Excluir e registrar o motivo |
| Linha igual nas 33 variáveis originais, dentro da mesma disciplina | Sinalizar e manter para revisão |
| Mesmos códigos e notas, com outras variáveis diferentes | Manter: pessoas diferentes podem ter os mesmos resultados |
| Nota final zero | Manter como nota válida, sem assumir que é ausência |
| Nota baixa em categoria alta de estudo ou outro padrão inesperado | Manter: não limpar para confirmar a hipótese |

A verificação de repetição usa os atributos completos somente durante o processamento;
não os exporta nem faz identificação entre disciplinas. Os domínios dos demais 29
atributos não são auditados, porque não são utilizados na análise preparada.

`ocorrencias.csv` guarda disciplina, posição, tipo, campo e motivo, sem reproduzir valores
inválidos. Uma observação excluída pode gerar vários motivos. Se houver alertas, o resumo
é provisório até o grupo revisar e documentar decisões. Eventuais correções devem ir para
uma cópia de entrada, com justificativa; não alterar o arquivo oficial.

## 4. Transformações e carga — Load

- Traduzir as categorias de `studytime`, sem inferir um ponto médio ou horas exatas.
- Acrescentar a disciplina para impedir mistura das análises.
- Preservar G1/G2/G3 na escala original e acrescentar `nota_final_0_10 = G3 / 2`.
- Calcular quantidades, médias de G3 e contagens de notas finais zero **por disciplina e faixa**.
- Arredondar apenas médias dos resumos para quatro casas decimais, após os cálculos.
- Salvar CSVs UTF-8 com BOM, separador `;` e vírgula decimal. No JSON, médias são números
  e resultados indisponíveis são `null`. Faixas vazias têm quantidade zero e média vazia.

| Arquivo em `data/processed/uci/` | Finalidade |
|---|---|
| `base_tratada.csv` | Observações minimizadas, com categorias e notas para análise |
| `resumo_faixas.csv` | Oito grupos: quatro por disciplina, com quantidades e médias |
| `ocorrencias.csv` | Registro de exclusões e revisões; apenas cabeçalho nesta execução |
| `qualidade.json` | Regras, proveniência, hashes das entradas e contagens por disciplina |

Os resultados são derivados da base real. A aquisição e o tratamento são a entrega desta
atividade. A etapa de [EDA e visualização](eda-visualizacao.md) já apresenta gráficos,
associação descritiva por postos e interpretação. Não foram feitos testes de significância.

## 5. Evidências do processamento

Na execução de 08/10/2026, o download oficial foi concluído às **10h56 (America/Sao_Paulo)**.
O manifesto local `data/raw/uci/manifesto.json` registra a aquisição em
`2026-10-08T13:56:18.551909+00:00`; o relatório `qualidade.json` registra o ETL em
`2026-10-08T13:56:37.124825+00:00`. Os hashes do pacote e dos CSVs coincidem com os
da execução anterior, e os três CSVs de saída mantiveram o mesmo conteúdo.

| Disciplina | Recebidos | Válidos | Excluídos | Linhas completas repetidas | G3=0 mantidos | Média G3 (0–20) |
|---|---:|---:|---:|---:|---:|---:|
| Português | 649 | 649 | 0 | 0 | 15 | 11,9060 |
| Matemática | 395 | 395 | 0 | 0 | 38 | 10,4152 |

Contagens das faixas, na ordem dos códigos 1 a 4:

- Português: **212, 305, 97 e 35**; soma 649.
- Matemática: **105, 198, 65 e 27**; soma 395.

Hashes dos CSVs oficiais preservados:

```text
student-por.csv: a7594a11d7771c0efe1a740824e0e833da9c4cad07c39a9766a874575563fb3f
student-mat.csv: e47f9ee225e1ee6e69b7564e6dac7123e80b8486677fe111f351964cef5dec80
```

Essas contagens e médias foram confrontadas com os arquivos originais nos testes. A
ausência de exclusões significa que as variáveis utilizadas passaram nas regras previstas;
não implica representatividade da população brasileira nem validação de toda a base.

## 6. Execução e reprodução

Requisito: Python 3.10 ou superior, sem pacotes externos. Na raiz do projeto:

```powershell
python scripts/coletar_uci.py
python scripts/etl.py
python -m unittest discover -s tests -v
```

Apenas a coleta requer internet. Quando o pacote já estiver local:

```powershell
python scripts/coletar_uci.py --arquivo data/raw/uci-student-performance.zip
```

Pastas alternativas:

```powershell
python scripts/coletar_uci.py --destino data/raw/uci-outra-versao
python scripts/etl.py --entrada data/raw/uci-outra-versao --saida data/processed/outra-versao
```

O ETL aceita somente os dois CSVs oficiais completos, e não o antigo modelo de respostas.
A saída deve ficar fora da pasta bruta. Reexecutar substitui os quatro produtos sem
acumular linhas; os originais continuam intactos. Os hashes e CSVs permanecem iguais
para a mesma entrada, mas o horário do relatório muda.

Código de saída do ETL: 0 quando ambas as disciplinas têm registros válidos; 1 em falha
de entrada; 2 quando alguma disciplina fica sem observações válidas. Código 0 não dispensa
revisão. `pronta_para_analise` indica registros válidos sem alertas, não aprovação humana
ou ausência de limitações. Falhas de entrada não atualizam saídas antigas.

Os **14 testes passaram, sem testes ignorados**, na execução de 08/10/2026. Os testes de código são independentes
de internet e usam casos artificiais isolados,
sem misturá-los à base real. O teste de integração com contagens oficiais é executado
quando os CSVs brutos estão disponíveis; em um clone novo, rodar a coleta antes dos testes
para incluir essa verificação.

## 7. Preparação para análise e metodologia

Importar os CSVs com delimitador `;` e localidade brasileira. Filtrar Português e usar
as categorias ordenadas 1 a 4. Para o gráfico de médias, usar `resumo_faixas.csv`; para
distribuição de notas, usar G3 da base tratada. Matemática deve permanecer em comparação
separada. Não calcular dispersão de horas exatas ou agrupar as linhas como pessoas únicas.

Para apoio de IA, utilizar preferencialmente o resumo agregado e informar escala,
categorias, disciplina e limitações. A base tratada não contém os atributos demográficos
ou de saúde presentes nos originais. Não tentar reidentificar participantes.

Texto de metodologia que já pode ser utilizado:

> Foram utilizados dados secundários públicos da base Student Performance, de Paulo
> Cortez (2008), disponibilizada pela UCI Machine Learning Repository. A fonte registra
> dados escolares de duas escolas portuguesas. Os arquivos oficiais foram obtidos em
> 08/10/2026, preservados e identificados por hashes SHA-256. O ETL verificou a estrutura
> e os domínios de studytime, G1, G2 e G3, sem imputação ou exclusão de notas zero.
> Foram preparados 649 registros de Português, utilizados como análise principal, e
> 395 de Matemática, mantidos separadamente. Não houve exclusões ou linhas completas
> repetidas. O tempo de estudo foi mantido em suas quatro categorias originais e a nota
> final G3 na escala de 0 a 20. Uma escala opcional de 0 a 10 foi obtida por divisão
> explícita por dois. A base minimizada e os resumos por faixa foram gerados para análise,
> respeitando a sobreposição de alunos e sem afirmar causalidade.

Referência, licença e adaptações estão em [data/README.md](../data/README.md).
