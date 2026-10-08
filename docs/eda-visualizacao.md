# EDA e visualização

Análise executada em **08/10/2026** a partir dos produtos existentes do ETL, sem nova
coleta. Português é a análise principal; Matemática é uma comparação separada.

## Entregas

- [Relatório visual HTML](../reports/eda/relatorio.html): indicadores, tabelas,
  oito gráficos, interpretação, método e limites. Abra em um navegador; funciona offline.
- [Relatório Markdown](../reports/eda/relatorio.md): resultados com imagens SVG.
- [Estatísticas CSV](../reports/eda/estatisticas.csv): G1/G2/G3 por disciplina e G3
  nas quatro faixas; quantidade, média, mediana, DP amostral, mínimo, quartis,
  máximo, notas zero e atípicos.
- [Correlações CSV](../reports/eda/correlacoes.csv): Spearman de studytime/G3,
  G1/G3 e G2/G3, sempre dentro da disciplina.
- [Indicadores JSON](../reports/eda/indicadores.json): cálculos sem arredondamento de
  apresentação, qualidade do ETL, horário UTC e SHA-256 das três entradas.
- [Gráficos](../reports/eda/graficos/): médias, boxplot, frequência de cada G3 e
  quantidade por faixa, em PNG e SVG, para cada disciplina.

As saídas contêm apenas agregados e figuras; não exportam posições de origem ou
atributos pessoais. CSVs usam UTF-8 com BOM, separador `;` e vírgula decimal.
Resultados indisponíveis ficam vazios no CSV, `null` no JSON e `—` no relatório.

## Resultados e padrões

Na escala original de **0 a 20**, Português tem média **11,91**, mediana **12**
e DP amostral **3,23**. Matemática tem média **10,42**, mediana **11** e DP **4,58**.
Os 649 e 395 registros são observações por disciplina, com alunos compartilhados entre
os arquivos. Não se calcula média escolar geral nem total de pessoas distintas.

| Faixa de estudo semanal | n Português | Média G3 Português | n Matemática | Média G3 Matemática |
|---|---:|---:|---:|---:|
| Menos de 2 horas | 212 | 10,84 | 105 | 10,05 |
| 2 a 5 horas | 305 | 12,09 | 198 | 10,17 |
| 5 a 10 horas | 97 | 13,23 | 65 | 11,40 |
| Mais de 10 horas | 35 | 13,06 | 27 | 11,26 |

As médias aumentam nas três primeiras faixas e caem ligeiramente na quarta, em ambas
as disciplinas. A maior média observada é a da faixa 5 a 10 horas. Não há crescimento
contínuo entre as quatro categorias. A diferença entre as faixas mais de 10 horas e
menos de 2 horas é **2,21 pontos em Português** e **1,21 em Matemática**.

Os grupos são desiguais: a faixa 2 a 5 horas concentra **47,0%** dos registros de
Português e **50,1%** dos de Matemática. Mais de 10 horas possui somente 35 e 27
registros. Os boxplots mostram dispersão e sobreposição entre faixas; as médias não
permitem prever individualmente a nota de um aluno.

Spearman de studytime/G3 é **0,275 em Português** e **0,105 em Matemática**.
Há associação positiva por postos, numericamente maior em Português, sem testar a
significância desses coeficientes ou da diferença entre eles. G1/G3 e G2/G3 têm
coeficientes maiores (0,883/0,944 em Português; 0,878/0,957 em Matemática). Isso
descreve a relação entre avaliações da mesma disciplina e não isola efeito do estudo.

As **15 notas zero de Português** e **38 de Matemática** permanecem em todos os
cálculos. Na distribuição geral de G3, a regra IQR sinaliza 16 atípicos em Português
e nenhum em Matemática. Isso não significa ausência de notas baixas em Matemática:
sua dispersão produz limites mais amplos. O critério é recalculado em cada faixa,
portanto a soma dos atípicos por faixa pode diferir do total da disciplina.

## Método e qualidade

O [script](../scripts/eda.py) valida o contrato da base tratada e confronta contagens,
médias e notas zero com `qualidade.json` e `resumo_faixas.csv`. Também verifica faixa,
conversão de escala e unicidade da posição dentro de cada disciplina. Não remove linhas
com notas iguais: registros diferentes podem apresentar os mesmos valores analíticos.
As entradas da execução tiveram zero campos analíticos ausentes e zero sinalizações.
Se o ETL tiver pendências, o relatório indica resultados provisórios.

- Média e mediana: calculadas diretamente das observações, incluindo zeros.
- Desvio-padrão: amostral, divisor n−1; indisponível para menos de dois registros.
- Quartis: interpolação linear no índice (n−1) × p, também chamada tipo 7.
- Atípicos: valores estritamente abaixo de Q1 − 1,5 × IQR ou acima de Q3 + 1,5 × IQR.
- Boxplot: caixa Q1–Q3 e mediana; bigodes nas observações dentro dos limites IQR;
  pontos fora deles. Pontos iguais podem se sobrepor. Nenhum atípico é excluído.
- Spearman: correlação de Pearson dos postos médios, respeitando empates. Categorias
  vazias, variáveis constantes e amostras insuficientes não recebem resultados inventados.

`studytime` é ordinal; não se usam seus códigos como horas exatas nem se calcula
uma média de horas. Não foram estimados p-valores, intervalos de confiança, regressões
ou efeitos causais. Os resultados descrevem dados observacionais históricos de duas
escolas portuguesas, com grupos desiguais e fatores não controlados, sem generalização
para estudantes da FATEC.

## Reprodução e verificação

Python 3.10+ e Matplotlib. Com os produtos do ETL na pasta padrão:

```powershell
python -m pip install -r requirements-eda.txt
python scripts/eda.py
python -m unittest discover -s tests -v
```

Pastas alternativas:

```powershell
python scripts/eda.py --entrada data/processed/uci --saida reports/eda
```

A saída deve ficar fora da pasta de entrada e dos dados brutos. Reexecutar atualiza
os artefatos, sem alterar o ETL ou seus produtos. Código de saída 0 indica sucesso;
1 indica entrada inválida, divergência com o ETL ou dependência ausente.

Nesta máquina, o comando `python` aponta para um alias indisponível da Microsoft Store.
A execução foi feita com o Python do runtime local do Codex e Matplotlib instalado
na pasta ignorada `.eda-deps`. Para repetir **neste ambiente**, em PowerShell:

```powershell
$pythonEda = 'C:\Users\danie\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$env:PYTHONPATH = (Join-Path (Get-Location) '.eda-deps')
& $pythonEda scripts/eda.py
& $pythonEda -m unittest discover -s tests -v
```

Foram aprovados **23 testes, sem testes ignorados**, incluindo os 14 existentes e nove
da EDA: quartis, DP, zeros e atípicos; postos empatados; categorias vazias; separação
de disciplinas; entrada inconsistente; proteção dos dados; reconciliação com a base
real; geração das figuras e preservação das entradas. Os gráficos foram inspecionados
visualmente para conferir rótulos, escala e legibilidade.

Fonte: Cortez, P. (2008). *Student Performance [Dataset]. UCI Machine Learning Repository*.
[DOI: 10.24432/C5TG7T](https://doi.org/10.24432/C5TG7T).
Licença: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Resumos e gráficos são derivados pelo projeto, mantendo a atribuição da fonte.
