# projeto-fatec-dsm

Projeto acadêmico de análise de dados: **Relação entre Tempo Semanal de Estudo e
Desempenho Escolar**, utilizando a base pública real
[Student Performance — UCI](https://archive.ics.uci.edu/dataset/320/student+performance).

O projeto compara notas finais entre as faixas de estudo semanal registradas na fonte.
**Português é a análise principal (649 registros)**; Matemática é uma comparação
separada (395 registros). Há alunos presentes nos dois arquivos: os 1.044 registros por
disciplina **não representam 1.044 alunos distintos**.

## Documentação

- [Plano do projeto](docs/projeto-horas-de-estudo-e-notas.md): problema, objetivos,
  metodologia, fórmulas, gráficos recomendados e estrutura do relatório.
- [Coleta, tratamento e ETL](docs/coleta-tratamento-etl.md): aquisição oficial,
  dicionário de dados, validação e evidências da execução.
- [EDA e visualização](docs/eda-visualizacao.md): indicadores, padrões, gráficos,
  interpretação e reprodução da análise.
- [Fonte e atribuição dos dados](data/README.md): referência, licença e adaptações.

## Dados preparados

- [Base tratada](data/processed/uci/base_tratada.csv).
- [Quantidades e médias por faixa e disciplina](data/processed/uci/resumo_faixas.csv).
- [Ocorrências](data/processed/uci/ocorrencias.csv) e
  [relatório de qualidade](data/processed/uci/qualidade.json).

Coleta e ETL reexecutados em **08/10/2026**, com os **14 testes aprovados**.
Os arquivos oficiais foram obtidos e processados: **649 registros válidos de Português
e 395 de Matemática, sem exclusões ou linhas completas repetidas**. As notas finais zero
foram preservadas. Não são dados simulados nem respostas coletadas pelo grupo.

`studytime` é uma categoria ordinal: 1 = menos de 2 horas; 2 = 2 a 5; 3 = 5 a 10;
4 = mais de 10. Esses códigos não são horas exatas. `G3` é a nota final da disciplina
na escala de 0 a 20. A coluna opcional `nota_final_0_10` equivale a `G3 / 2`, com a nota
original preservada. Não existe média geral escolar nesta base.

## Reproduzir a coleta e o ETL

Requisito: **Python 3.10+**, sem pacotes externos. Na raiz do projeto:

```powershell
python scripts/coletar_uci.py
python scripts/etl.py
```

A coleta baixa o pacote HTTPS oficial e extrai os dois CSVs e o dicionário em
`data/raw/uci/`. Registra fonte, licença, data de obtenção e hashes em `manifesto.json`.
Os arquivos brutos ficam locais e ignorados pelo Git; a base tratada e os resumos
podem ser versionados. O ETL gera as saídas em `data/processed/uci/`.

Para um pacote oficial já baixado:

```powershell
python scripts/coletar_uci.py --arquivo data/raw/uci-student-performance.zip
```

Para verificar o código:

```powershell
python -m unittest discover -s tests -v
```

## EDA e visualização

A análise exploratória foi executada em **08/10/2026**, com **23 testes aprovados**,
sem testes ignorados. Abra o [relatório visual](reports/eda/relatorio.html) em um navegador
ou consulte o [relatório Markdown](reports/eda/relatorio.md).

Foram gerados indicadores de média, mediana, desvio-padrão amostral, quartis, notas zero,
valores atípicos e correlações de Spearman. São **oito gráficos**, disponíveis em PNG e
SVG: médias por faixa, boxplots, distribuição de G3 e quantidade por faixa, para cada
disciplina. [Estatísticas CSV](reports/eda/estatisticas.csv),
[correlações CSV](reports/eda/correlacoes.csv) e
[indicadores JSON](reports/eda/indicadores.json) permitem reutilizar os resultados.

**Achado principal:** em Português, a média de G3 passa de 10,84 na faixa menos de
2 horas para 13,23 na faixa 5 a 10 horas, e fica em 13,06 na faixa mais de 10 horas.
Há associação positiva por postos (Spearman = 0,275), sem crescimento contínuo das
quatro médias e sem demonstração de causalidade. Os grupos têm 212, 305, 97 e 35 registros.

Para reproduzir, com a base tratada disponível:

```powershell
python -m pip install -r requirements-eda.txt
python scripts/eda.py
python -m unittest discover -s tests -v
```

A coleta e o ETL continuam sem dependências externas; apenas os gráficos usam Matplotlib.
A EDA funciona offline depois da instalação e confronta a base com `qualidade.json`
e `resumo_faixas.csv` antes de gerar saídas. Também aceita `--entrada` e `--saida`.
Consulte o [guia da EDA](docs/eda-visualizacao.md) para detalhes do ambiente local.

## Privacidade e referência

A base analítica carrega somente disciplina, posição de origem, faixa de estudo e notas.
Os atributos demográficos, familiares e de saúde do arquivo original não são carregados.
Para apoio de IA, usar preferencialmente os resumos agregados, sem posições de origem.
Não tentar identificar ou relacionar alunos entre arquivos.

Fonte: Cortez, P. (2008). *Student Performance [Dataset]. UCI Machine Learning Repository*.
[DOI: 10.24432/C5TG7T](https://doi.org/10.24432/C5TG7T).
Licença: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Este projeto seleciona variáveis, traduz rótulos, acrescenta uma conversão explícita de
escala e calcula resumos; não altera os arquivos oficiais.
