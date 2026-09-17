# Dados: Student Performance — UCI

## Fonte e atribuição

Cortez, P. (2008). **Student Performance [Dataset]**. UCI Machine Learning Repository.
[DOI: 10.24432/C5TG7T](https://doi.org/10.24432/C5TG7T).

- [Página oficial e dicionário de variáveis](https://archive.ics.uci.edu/dataset/320/student+performance).
- [Pacote oficial de download](https://archive.ics.uci.edu/static/public/320/student%2Bperformance.zip).
- Licença indicada pelo repositório: [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/).

A fonte descreve dados reais de duas escolas de ensino secundário em Portugal, obtidos
por questionários e registros escolares. Há dois arquivos, um por disciplina. O ano de
2008 é o da referência do dataset; a data de download não é a data da coleta escolar.

## Organização

- `raw/uci/`: CSVs originais (`student-por.csv`, `student-mat.csv`), dicionário
  `student.txt` e manifesto de aquisição. Ignorados pelo Git, recriados pelo coletor.
- `processed/uci/`: base minimizada, resumo por faixa, ocorrências e qualidade.
  Produtos do ETL prontos para consulta e importação em planilha.

O pacote externo contém `student.zip`; o coletor usa essa versão e ignora o arquivo
antigo `.student.zip_old`. São extraídos somente os três arquivos necessários, sem
executar o script R incluído na fonte.

## Adaptações e limites

As transformações deste projeto são: seleção de `studytime`, `G1`, `G2` e `G3`;
inclusão de disciplina e posição de origem; tradução das faixas; inclusão da escala
opcional `G3 / 2`; padronização do CSV e cálculo de quantidades e médias por disciplina.
Os arquivos originais são preservados byte a byte. A licença e a atribuição acima
acompanham os dados tratados; não se declara autoria sobre as observações escolares.

`studytime` não informa horas exatas. Seus intervalos não são os do antigo questionário.
`G3` não é média geral escolar. Os dois arquivos têm alunos em comum e não devem ser
somados como pessoas distintas. Nenhuma ligação entre alunos é feita neste projeto.

G3=0 é mantido como nota válida. Não há imputação nem exclusão de valores apenas por
parecerem atípicos. Colunas contextuais da fonte, como idade, escola, família, saúde e
consumo de álcool, não integram os dados analíticos entregues.
