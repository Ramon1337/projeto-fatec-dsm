# Mineração, modelagem e validação

Etapa executada em **08/11/2026**, usando a base real já tratada pelo ETL.
Português continua como análise principal (649 registros), com Matemática como
comparação separada (395). Os registros das disciplinas não são alunos distintos.

## Entregas

- [Relatório visual](../reports/modelagem/relatorio.html) e
  [relatório completo em Markdown](../reports/modelagem/relatorio.md).
- [Script reproduzível](../scripts/modelagem.py).
- [Métricas dos 18 modelos](../reports/modelagem/metricas.csv),
  [padrões de treino](../reports/modelagem/padroes_treino.csv) e
  [avaliação por faixa no teste](../reports/modelagem/teste_por_faixa.csv).
- [Resultados e rastreabilidade](../reports/modelagem/resultados.json): todas as
  configurações e seus resultados por dobra, seleção, partições, ambiente e hashes.
- [Gráficos](../reports/modelagem/graficos/): comparação de MAE por disciplina,
  nos formatos PNG e SVG.
- [Modelos selecionados](../reports/modelagem/modelos/): seis descrições TXT com
  regras/constantes/coeficientes e preparo das entradas. Os seis Pipelines joblib são
  gerados localmente, ignorados pelo Git e podem ser recriados pelo script.

Os CSVs usam UTF-8 com BOM, `;` e vírgula decimal. As saídas versionáveis contêm
agregados, parâmetros ou regras, sem previsões individuais ou posições de origem.
Os modelos servem ao estudo acadêmico; não foram preparados como serviço em produção.

## Mineração dos padrões

A mineração descritiva agrupa as observações por faixa e calcula suporte, média de G3
e diferença para a média geral, **somente nos registros de treino**. Spearman resume
a associação ordinal e eta² resume a fração da soma de quadrados de G3 associada às
diferenças entre as médias dos grupos. Não são testes de significância ou efeitos causais.
As árvores acrescentam regras interpretáveis de previsão, registradas nos arquivos TXT.

Em Português, Spearman no treino foi **0,278** e eta² **0,067**. A maior média no treino
foi **13,22**, na faixa 5 a 10 horas (78 registros). Em Matemática, Spearman foi **0,081**
e eta² **0,011**. Esses valores usam apenas o treino e podem diferir dos da EDA completa.
`studytime` continua categórico: seus códigos não representam horas exatas.

## Construção e seleção dos modelos

O alvo é G3 na escala original de 0 a 20. Foram comparadas três famílias:

1. **Referência pela mediana:** constante estimada no treino, apropriada à minimização
   do erro absoluto médio (MAE).
2. **Regressão Ridge:** penalização L2 com alpha em 0,1; 1; 10; 100.
3. **Árvore de regressão:** perda absoluta, profundidade máxima 2; 3; 5 e mínimo de
   registros por folha 5 ou 15.

São três cenários em cada disciplina: somente `studytime`; somente G1/G2 (controle);
e `studytime` + G1/G2. O controle permite verificar se adicionar estudo traz ganho
além das notas anteriores. Os cenários com G1/G2 pressupõem que essas avaliações
já aconteceram; não são previsões para o início do ano letivo.

As faixas passam por one-hot; as notas anteriores passam por padronização. O
`Pipeline` contém todo o preparo e o estimador, ajustados novamente em cada dobra.
G3, `nota_final_0_10`, disciplina e posição de origem nunca entram como atributos.
Não há exclusão de zeros/atípicos, imputação, arredondamento ou truncamento de previsões.
Eventuais previsões fora da escala são contabilizadas.

## Validação e avaliação

A separação aleatória usa semente **42**, com **80% para treino e 20% para teste**, e
estratificação pela faixa. Português tem **519/130** registros; Matemática, **316/79**.
As partições são idênticas nos três cenários de cada disciplina e permanecem separadas
entre disciplinas. Não se tenta relacionar alunos dos dois arquivos.

A validação cruzada de **cinco partes**, restrita ao treino e estratificada por faixa,
escolhe hiperparâmetros e família pelo menor MAE médio, incluindo a referência.
Empates favorecem mediana, Ridge e árvore, nessa ordem. São 11 configurações por
cenário. O teste é consultado após congelar a seleção, e os modelos persistidos
continuam ajustados somente no treino. As métricas de todas as famílias são publicadas
para transparência, sem trocar o selecionado pelo vencedor no teste.

MAE é o erro absoluto médio; RMSE dá maior peso a erros grandes. Ambos são pontos de
G3. R² pode ser negativo, não é acurácia nem percentual de acertos. Viés é a média
de previsto menos observado. O DP do MAE nas dobras descreve variação, não é intervalo
de confiança; a própria CV de seleção não constitui avaliação final independente.

| Disciplina | Cenário | Selecionado por CV | MAE teste | RMSE teste | R² teste |
|---|---|---|---:|---:|---:|
| Português | Somente faixa | Árvore | 2,369 | 3,305 | 0,069 |
| Português | Somente G1/G2 | Árvore | 0,654 | 1,147 | 0,888 |
| Português | Faixa + G1/G2 | Árvore | 0,704 | 1,205 | 0,876 |
| Matemática | Somente faixa | Mediana | 3,304 | 4,163 | -0,000009 |
| Matemática | Somente G1/G2 | Árvore | 0,937 | 1,889 | 0,794 |
| Matemática | Faixa + G1/G2 | Árvore | 1,114 | 2,240 | 0,710 |

A referência teve MAE de **2,531** em Português e **3,304** em Matemática. Usando apenas
a faixa, a redução do MAE foi **6,38%** em Português; em Matemática, a própria referência
foi selecionada. Assim, a faixa isolada ofereceu pouca capacidade preditiva nesta divisão.

G1/G2 reduziram bastante o erro. Acrescentar a faixa aos modelos selecionados com notas
anteriores aumentou o MAE em **0,050** ponto em Português e **0,177** em Matemática.
Não houve ganho adicional observado para os modelos selecionados nesta execução.
A comparação também envolve configurações escolhidas separadamente; não prova
irrelevância universal da variável nem significância da diferença. Ridge apresentou
alguns resultados de teste melhores em cenários complementares, mas a seleção por CV
foi mantida. Duas configurações Ridge finais produziram uma previsão fora de 0–20 cada,
em Matemática; esses valores foram mantidos na avaliação, sem ajuste posterior.

## Limites

A validação é interna e usa uma única divisão aleatória. O teste reservado nesta
rotina já pertence a uma base explorada pela EDA: não equivale a dados externos nunca
examinados. Não há validação externa/temporal, estimativa de efeito causal, p-valores ou
intervalos de confiança. As faixas maiores têm poucos registros no teste (7 em Português
e 5 em Matemática), limitando a estabilidade das métricas por grupo.

São dados observacionais históricos de duas escolas portuguesas; os resultados não
podem ser generalizados automaticamente para a FATEC. G1/G2 refletem o desempenho
anterior na mesma disciplina. A associação com G3 não demonstra efeito do estudo.

## Reprodução e verificação

Use Python com as dependências de modelagem; o ambiente verificado foi **Python
3.12.14 em Windows x64**. Na raiz do projeto, com os produtos do ETL disponíveis:

```powershell
python -m pip install -r requirements-modelagem-lock.txt
python scripts/modelagem.py
python -m unittest discover -s tests -v
```

O arquivo `requirements-modelagem-lock.txt` registra as versões exatas desta execução;
`requirements-modelagem.txt` aceita intervalos de versões para outros ambientes.
Depois de instalar, a análise funciona offline. Aceita `--entrada` e `--saida`;
a saída deve ficar fora das entradas, dos dados e das pastas das demais etapas.
O script reconcilia a base com os resumos e a qualidade do ETL e rejeita pendências
antes de ajustar modelos. Cada execução atualiza as saídas e o horário de rastreio.

Nesta máquina, o alias `python` da Microsoft Store está indisponível. Foi utilizado
o runtime local e uma pasta de dependências ignorada pelo Git:

```powershell
$pythonModelo = 'C:\Users\danie\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$env:PYTHONPATH = (Join-Path (Get-Location) '.modelagem-deps')
& $pythonModelo -m pip install --target .modelagem-deps -r requirements-modelagem-lock.txt
& $pythonModelo scripts/modelagem.py
& $pythonModelo -m unittest discover -s tests -v
```

Foram aprovados **32 testes, sem testes ignorados**: os 23 existentes e nove da nova
etapa. Verificam métricas, zeros, partições disjuntas, cobertura das dobras, reprodução,
atributos proibidos, invariância da seleção e do preparo a alterações no teste,
mineração em dados conhecidos, bloqueio de entradas inconsistentes, preservação dos
dados e recarga dos modelos persistidos. Os gráficos foram inspecionados visualmente.

Referências técnicas: [Pipelines e prevenção de vazamento](https://scikit-learn.org/stable/common_pitfalls.html),
[GridSearchCV](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GridSearchCV.html)
e [métricas de avaliação](https://scikit-learn.org/stable/modules/model_evaluation.html).
Fonte: [Cortez (2008), Student Performance/UCI](https://doi.org/10.24432/C5TG7T),
licença [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
