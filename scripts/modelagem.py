"""Mineração descritiva, regressão e validação interna da base UCI tratada."""

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
from html import escape
import json
import os
from pathlib import Path
import platform
import sys

try:
    from scripts.eda import load_base, reconcile, spearman, fmt, SLUGS
    from scripts.etl import BANDS, write_csv
except ModuleNotFoundError:  # Execução direta na raiz do projeto.
    from eda import load_base, reconcile, spearman, fmt, SLUGS
    from etl import BANDS, write_csv

ROOT = Path(__file__).resolve().parents[1]
SEED = 42
SCENARIOS = {
    "somente_estudo": ("Somente faixa de estudo", ("studytime",)),
    "notas_anteriores": ("Somente G1 e G2 (controle)", ("G1", "G2")),
    "estudo_e_notas": ("Faixa de estudo + G1 e G2", ("studytime", "G1", "G2")),
}
LABELS = {"mediana": "Mediana (referência)", "ridge": "Regressão Ridge", "arvore": "Árvore de regressão"}
METRIC_FIELDS = ("disciplina", "cenario", "modelo", "selecionado_cv", "cv_mae", "cv_dp_mae",
                 "treino_mae", "teste_mae", "teste_rmse", "teste_r2", "teste_vies", "teste_fora_escala")
METHOD = (
    "Alvo: G3, escala 0–20. Separação aleatória 80% treino / 20% teste, semente 42, "
    "estratificada pela faixa de estudo, dentro de cada disciplina. Os três cenários usam "
    "exatamente as mesmas partições. Validação cruzada de cinco partes no treino, também "
    "estratificada por faixa. GridSearchCV escolhe hiperparâmetros pelo menor MAE médio; "
    "o menor MAE de CV entre famílias (incluindo a referência) define o modelo selecionado "
    "antes de consultar o teste. Empates favorecem a ordem mediana, Ridge, árvore. "
    "One-hot para studytime, sem tratá-lo como horas ou impor intervalos iguais. "
    "G1/G2 são padronizadas dentro do Pipeline; cada ajuste usa somente o treino da dobra. "
    "Não há imputação, remoção de zeros, arredondamento ou truncamento de previsões. "
    "Os modelos finais são ajustados somente nos 80% de treino."
)
LIMITS = (
    "Validação interna, em uma única divisão aleatória de dados históricos de duas escolas "
    "portuguesas. Não mede transferência para outras escolas, épocas ou alunos da FATEC. "
    "Não há validação externa ou temporal, intervalos de confiança ou testes de significância. "
    "O desvio-padrão do MAE nas dobras descreve variação; não é intervalo de confiança. "
    "A CV utilizada para escolher configurações é otimista como estimativa final; o teste "
    "reservado fornece a avaliação final. Resultados por faixa têm amostras pequenas. "
    "Há alunos compartilhados entre disciplinas: elas não são reunidas, nem tratadas como "
    "replicações independentes. A fonte já foi explorada na EDA; o teste é reservado nesta "
    "rotina de ajuste, sem equivaler a uma amostra externa nunca examinada. G1/G2 só estão "
    "disponíveis após os períodos anteriores; esses cenários não servem para previsão no "
    "início do ano. Modelos e padrões não demonstram causalidade nem isolam efeito do estudo."
)


def metrics(y, prediction):
    import numpy as np
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    y, prediction = np.asarray(y), np.asarray(prediction)
    return {"mae": float(mean_absolute_error(y, prediction)),
            "rmse": float(np.sqrt(mean_squared_error(y, prediction))),
            "r2": float(r2_score(y, prediction)) if len(y) > 1 and np.ptp(y) else None,
            "vies": float(np.mean(prediction - y)),
            "fora_escala": int(np.sum((prediction < 0) | (prediction > 20)))}


def split_data(rows):
    import numpy as np
    from sklearn.model_selection import StratifiedKFold, train_test_split
    bands = np.array([row["studytime"] for row in rows])
    if set(bands) != set(BANDS) or min(Counter(bands).values()) < 10:
        raise ValueError("São necessários ao menos dez registros em cada uma das quatro faixas.")
    train, test = train_test_split(np.arange(len(rows)), test_size=.2, random_state=SEED, stratify=bands)
    folds = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED).split(train, bands[train]))
    return train, test, folds


def features(rows, fields):
    """Lista explícita: nunca incluir G3, sua conversão ou posição de origem em X."""
    import numpy as np
    if tuple(fields) not in [item[1] for item in SCENARIOS.values()]:
        raise ValueError("Conjunto de atributos não autorizado para os modelos.")
    return np.array([[row[field] for field in fields] for row in rows], dtype=float)


def candidates(fields):
    from sklearn.compose import ColumnTransformer
    from sklearn.dummy import DummyRegressor
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from sklearn.tree import DecisionTreeRegressor
    transforms = []
    if "studytime" in fields:
        transforms.append(("faixa", OneHotEncoder(categories=[[1, 2, 3, 4]],
                                                handle_unknown="error", sparse_output=False),
                           [fields.index("studytime")]))
    grade_indices = [fields.index(field) for field in ("G1", "G2") if field in fields]
    if grade_indices:
        transforms.append(("notas", StandardScaler(), grade_indices))
    for name, estimator, grid in (
        ("mediana", DummyRegressor(strategy="median"), {}),
        ("ridge", Ridge(), {"modelo__alpha": [.1, 1., 10., 100.]}),
        ("arvore", DecisionTreeRegressor(random_state=SEED, criterion="absolute_error"),
         {"modelo__max_depth": [2, 3, 5], "modelo__min_samples_leaf": [5, 15]}),
    ):
        yield name, Pipeline([("preparo", ColumnTransformer(transforms)), ("modelo", estimator)]), grid


def mine_training(rows):
    """Padrões de grupo calculados exclusivamente no treino; eta² é descritivo."""
    import numpy as np
    y = np.array([row["G3"] for row in rows], dtype=float)
    average = float(y.mean())
    total = float(np.sum((y - average) ** 2))
    groups = []
    for code, label in BANDS.items():
        grades = y[[row["studytime"] == code for row in rows]]
        groups.append({"studytime": code, "faixa_estudo": label, "quantidade": len(grades),
                       "suporte": len(grades) / len(y), "media_g3": float(grades.mean()),
                       "diferenca_media_geral": float(grades.mean() - average)})
    between = sum(g["quantidade"] * (g["media_g3"] - average) ** 2 for g in groups)
    return {"quantidade": len(y), "media_g3": average, "faixas": groups,
            "eta_quadrado": between / total if total else None,
            "spearman": spearman([row["studytime"] for row in rows], y.tolist())}


def fit_scenario(rows, fields, train, test, folds):
    import numpy as np
    from sklearn.model_selection import GridSearchCV
    x = features(rows, fields)
    y = np.array([row["G3"] for row in rows], dtype=float)
    searches, records, tuning = {}, [], []
    # Nenhuma consulta a y[test] até congelar a seleção das famílias.
    for name, pipeline, grid in candidates(fields):
        search = GridSearchCV(pipeline, grid, scoring="neg_mean_absolute_error", cv=folds,
                              refit=True, n_jobs=1, error_score="raise")
        search.fit(x[train], y[train])
        searches[name] = search
        for index, params in enumerate(search.cv_results_["params"]):
            tuning.append({"modelo": name, "parametros": params,
                           "cv_mae": -float(search.cv_results_["mean_test_score"][index]),
                           "cv_dp_mae": float(search.cv_results_["std_test_score"][index]),
                           "mae_dobras": [-float(search.cv_results_[f"split{k}_test_score"][index]) for k in range(5)]})
    selected = min(searches, key=lambda name: -searches[name].best_score_)
    for name, search in searches.items():
        prediction = search.predict(x[test])
        train_metrics = metrics(y[train], search.predict(x[train]))
        test_metrics = metrics(y[test], prediction)
        records.append({"modelo": name, "selecionado_cv": name == selected,
                        "parametros": search.best_params_, "cv_mae": -float(search.best_score_),
                        "cv_dp_mae": float(search.cv_results_["std_test_score"][search.best_index_]),
                        "treino_mae": train_metrics["mae"],
                        **{"teste_" + key: value for key, value in test_metrics.items()}})
    chosen = searches[selected].best_estimator_
    prediction = chosen.predict(x[test])
    baseline = searches["mediana"].predict(x[test])
    per_band = []
    for code, label in BANDS.items():
        mask = np.array([rows[int(i)]["studytime"] == code for i in test])
        per_band.append({"studytime": code, "faixa_estudo": label, "quantidade": int(mask.sum()),
                         **metrics(y[test][mask], prediction[mask]),
                         "mae_referencia": metrics(y[test][mask], baseline[mask])["mae"]})
    return {"atributos": list(fields), "selecionado": selected, "modelos": records,
            "busca_cv": tuning, "teste_por_faixa": per_band}, chosen


def conclusions(subject, data):
    texts = []
    for scenario, (label, _) in SCENARIOS.items():
        item = data["cenarios"][scenario]
        chosen = next(model for model in item["modelos"] if model["selecionado_cv"])
        baseline = next(model for model in item["modelos"] if model["modelo"] == "mediana")
        gain = 100 * (1 - chosen["teste_mae"] / baseline["teste_mae"]) if baseline["teste_mae"] else None
        comparison = f"variação do MAE frente à referência: {fmt(gain)}% de redução" if gain is not None else "referência com MAE zero"
        texts.append(f"{label}: seleção por CV = {LABELS[item['selecionado']]}; "
                     f"MAE de teste {fmt(chosen['teste_mae'])}, RMSE {fmt(chosen['teste_rmse'])} e "
                     f"R² {fmt(chosen['teste_r2'], 3)}; {comparison}. Uma redução negativa indica piora.")
    study = data["mineracao_treino"]
    texts.append(f"No treino de {subject}, Spearman estudo/G3 = {fmt(study['spearman'], 3)} e "
                 f"eta² = {fmt(study['eta_quadrado'], 3)}. Eta² é a fração descritiva da soma de "
                 "quadrados de G3 associada às diferenças de médias entre faixas, sem interpretação causal.")
    control = data["cenarios"]["notas_anteriores"]
    full = data["cenarios"]["estudo_e_notas"]
    control_mae = next(m["teste_mae"] for m in control["modelos"] if m["selecionado_cv"])
    full_mae = next(m["teste_mae"] for m in full["modelos"] if m["selecionado_cv"])
    texts.append(f"Ao acrescentar a faixa a G1/G2, a diferença de MAE de teste entre os modelos "
                 f"selecionados é {fmt(full_mae - control_mae, 3)} ponto(s) (com faixa menos controle; "
                 "valor negativo indica menor erro). Essa comparação também pode refletir "
                 "configurações distintas escolhidas por CV; não estima um efeito causal ou significância.")
    return texts


def charts(result, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "svg.fonttype": "none",
                         "svg.hashsalt": "uci-modelagem", "axes.spines.top": False, "axes.spines.right": False})
    folder = output / "graficos"
    folder.mkdir(exist_ok=True)
    for subject, slug in SLUGS.items():
        fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)
        for axis, (scenario, (label, _)) in zip(axes, SCENARIOS.items()):
            models = result["disciplinas"][subject]["cenarios"][scenario]["modelos"]
            x = np.arange(len(models))
            axis.bar(x - .18, [m["cv_mae"] for m in models], .36, label="CV no treino", color="#217e91")
            bars = axis.bar(x + .18, [m["teste_mae"] for m in models], .36, label="Teste reservado", color="#d28a35")
            axis.bar_label(bars, fmt="%.2f", padding=3, fontsize=9)
            axis.set_xticks(x, [LABELS[m["modelo"]].replace(" (referência)", "") + (" *" if m["selecionado_cv"] else "") for m in models], rotation=20, ha="right")
            axis.set_title(label, fontsize=11)
            axis.set_ylim(bottom=0)
        axes[0].set_ylabel("MAE · pontos da nota G3 (0–20) · menor é melhor")
        axes[0].legend(fontsize=9)
        fig.suptitle(f"{subject} · comparação de modelos\n* Selecionado pelo MAE de CV; teste não participa da escolha", fontsize=14)
        fig.tight_layout()
        for suffix in ("svg", "png"):
            fig.savefig(folder / f"{slug}_comparacao.{suffix}", dpi=160, bbox_inches="tight")
        plt.close(fig)


def model_summary(model, fields):
    """Descrição legível do modelo ajustado e do preparo das entradas."""
    from sklearn.dummy import DummyRegressor
    from sklearn.linear_model import Ridge
    from sklearn.tree import export_text
    preparation = model.named_steps["preparo"]
    estimator = model.named_steps["modelo"]
    names = preparation.get_feature_names_out(list(fields)).tolist()
    lines = ["Modelo ajustado somente no treino (80%); alvo G3 na escala 0–20.",
             "Atributos de entrada, nesta ordem: " + ", ".join(fields),
             "Faixas são indicadores one-hot (0/1), sem distâncias em horas."]
    if "notas" in preparation.named_transformers_:
        scaler = preparation.named_transformers_["notas"]
        lines += ["Nas regras/coeficientes, as notas são z = (nota - média) / escala.",
                  "Ordem das notas: G1, G2.", "Médias de treino: " + str(scaler.mean_.tolist()),
                  "Escalas de treino: " + str(scaler.scale_.tolist())]
    if isinstance(estimator, DummyRegressor):
        lines.append("Previsão constante (mediana de treino): " + str(float(estimator.constant_[0, 0])))
    elif isinstance(estimator, Ridge):
        lines += ["Intercepto: " + str(float(estimator.intercept_))]
        lines += [f"{name}: {float(coefficient)}" for name, coefficient in zip(names, estimator.coef_)]
    else:
        lines.append(export_text(estimator, feature_names=names, decimals=4))
    return "\n".join(lines) + "\n"


def reports(result, output):
    md = ["# Mineração, modelagem e validação", "Previsão da nota final G3 · escala 0–20. "
          "Português é a análise principal; Matemática é comparação separada.", "## Método", METHOD,
          "A referência prevê a mediana do treino, adequada ao MAE. Ridge usa alpha em "
          "{0,1; 1; 10; 100}; a árvore usa perda absoluta, profundidade em {2; 3; 5} e mínimo "
          "de registros por folha em {5; 15}. São 11 configurações por cenário. "
          "MAE é o erro absoluto médio; RMSE penaliza erros grandes; ambos estão em pontos "
          "de G3. R² pode ser negativo e não é percentual de acertos. Viés = média(previsto − real)."]
    sections = []
    for subject, slug in SLUGS.items():
        data = result["disciplinas"][subject]
        split = data["particao"]
        intro = f"{split['treino']} registros no treino e {split['teste']} no teste. Notas zero preservadas: {split['zeros_treino']} no treino e {split['zeros_teste']} no teste."
        md += [f"## {subject}", intro, *conclusions(subject, data)]
        paragraphs = "".join(f"<p>{escape(line)}</p>" for line in conclusions(subject, data))
        tables = []
        for scenario, (label, _) in SCENARIOS.items():
            item = data["cenarios"][scenario]
            header = ("Modelo", "MAE CV", "DP CV", "MAE treino", "MAE teste", "RMSE teste", "R² teste", "Viés teste", "Fora 0–20")
            md += [f"### {label}", "| " + " | ".join(header) + " |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
            body = []
            for model in item["modelos"]:
                values = [LABELS[model["modelo"]] + (" *" if model["selecionado_cv"] else "")]
                values += [fmt(model[key], 3) for key in ("cv_mae", "cv_dp_mae", "treino_mae", "teste_mae", "teste_rmse", "teste_r2", "teste_vies")]
                values.append(str(model["teste_fora_escala"]))
                md.append("| " + " | ".join(values) + " |")
                body.append("<tr>" + "".join(f"<td>{escape(v)}</td>" for v in values) + "</tr>")
            chosen = next(m for m in item["modelos"] if m["selecionado_cv"])
            params = "Configuração selecionada: " + json.dumps(chosen["parametros"], ensure_ascii=False) + f". Previsões de teste fora de 0–20: {chosen['teste_fora_escala']}."
            md += [params, "| Faixa no teste | n | MAE selecionado | MAE referência |", "|---|---:|---:|---:|"]
            for band in item["teste_por_faixa"]:
                md.append(f"| {band['faixa_estudo']} | {band['quantidade']} | {fmt(band['mae'], 3)} | {fmt(band['mae_referencia'], 3)} |")
            tables.append(f"<h3>{escape(label)}</h3><div class='scroll'><table><thead><tr>" + "".join(f"<th>{h}</th>" for h in header) + "</tr></thead><tbody>" + "".join(body) + f"</tbody></table></div><p>{escape(params)}</p>")
        md += ["### Padrões encontrados no treino", "Os suportes são proporções do treino da disciplina. "
               "Os padrões foram extraídos sem usar as notas do teste.",
               "| Faixa | n treino | Suporte | Média G3 | Diferença da média geral |", "|---|---:|---:|---:|---:|"]
        pattern_html = []
        for band in data["mineracao_treino"]["faixas"]:
            md.append(f"| {band['faixa_estudo']} | {band['quantidade']} | {fmt(100 * band['suporte'])}% | {fmt(band['media_g3'])} | {fmt(band['diferenca_media_geral'])} |")
            values = (band["faixa_estudo"], str(band["quantidade"]), fmt(100 * band["suporte"]) + "%", fmt(band["media_g3"]), fmt(band["diferenca_media_geral"]))
            pattern_html.append("<tr>" + "".join(f"<td>{escape(v)}</td>" for v in values) + "</tr>")
        md += [f"![Comparação de MAE em {subject}](graficos/{slug}_comparacao.svg)"]
        patterns = "<h3>Padrões encontrados no treino</h3><p>Suporte = proporção de registros do treino da disciplina.</p><div class='scroll'><table><thead><tr><th>Faixa</th><th>n treino</th><th>Suporte</th><th>Média G3</th><th>Diferença da média geral</th></tr></thead><tbody>" + "".join(pattern_html) + "</tbody></table></div>"
        sections.append(f"<section id='{slug}'><h2>{subject}</h2><p>{intro}</p>{paragraphs}" + "".join(tables) + patterns + f"<figure><img src='graficos/{slug}_comparacao.svg' alt='MAE de treino por CV e de teste dos modelos de {subject}'></figure></section>")
    source = "Fonte: [Cortez (2008), Student Performance/UCI](https://doi.org/10.24432/C5TG7T). Licença: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Modelos, tabelas e gráficos derivados pelo projeto."
    provenance = f"Execução UTC: {result['executado_em_utc']}. SHA-256 da base: {result['entradas_sha256']['base_tratada.csv']}. Ambiente: {json.dumps(result['ambiente'], ensure_ascii=False)}."
    md += ["## Limitações e interpretação", LIMITS, "## Rastreabilidade e artefatos", provenance,
           "resultados.json contém métricas completas, busca de hiperparâmetros, contagens por "
           "faixa e hashes das partições. metricas.csv resume os 18 modelos. padroes_treino.csv "
           "e teste_por_faixa.csv contêm somente agregados. modelos/ contém seis Pipelines "
           "selecionados em joblib, gerados localmente e ignorados pelo Git; incluem o preparo "
           "ajustado somente no treino. Arquivos TXT na mesma pasta descrevem as regras, "
           "constantes ou coeficientes e a padronização. Só carregar arquivos joblib de origem confiável. "
           "Não são exportadas previsões individuais ou posições de origem.", source,
           "Referências técnicas: [prevenção de vazamento com Pipelines](https://scikit-learn.org/stable/common_pitfalls.html), "
           "[GridSearchCV](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GridSearchCV.html) e "
           "[métricas de regressão](https://scikit-learn.org/stable/modules/model_evaluation.html)."]
    text = ""
    previous = ""
    for block in md:
        text += (("\n" if previous.startswith("|") and block.startswith("|") else "\n\n") if text else "") + block
        previous = block
    (output / "relatorio.md").write_text(text + "\n", encoding="utf-8")
    html = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Mineração, modelagem e validação · UCI</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#f3f6f7;color:#18313b;font:16px/1.6 system-ui,sans-serif}}
header{{background:#123b48;color:white;padding:36px max(24px,calc((100vw - 1160px)/2))}}h1{{line-height:1.2}}main{{max-width:1210px;margin:auto;padding:24px}}
section{{background:white;padding:28px;margin-bottom:24px;border:1px solid #dbe5e8;border-radius:14px}}.scroll{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;font-size:14px}}
th,td{{padding:10px;border-bottom:1px solid #dbe5e8;text-align:right;white-space:nowrap}}th:first-child,td:first-child{{text-align:left}}th{{background:#edf5f5}}
figure{{margin:20px 0}}img{{width:100%;height:auto}}a{{color:#155e75}}.provenance{{overflow-wrap:anywhere;font-size:13px}}
@media(max-width:700px){{main{{padding:12px}}section{{padding:16px}}}}@media print{{section{{border:0}}body{{background:white}}}}</style></head>
<body><header><p>Projeto FATEC DSM · Student Performance/UCI</p><h1>Mineração, modelagem e validação</h1><p>Nota final G3 · escala 0–20 · validação interna</p></header><main>
<section><h2>Método e leitura</h2><p>{escape(METHOD)}</p><p>* Selecionado pelo MAE de CV. MAE/RMSE menores são melhores. R² pode ser negativo; não é acurácia. DP CV não é intervalo de confiança. A referência prevê a mediana do treino. O controle G1/G2 permite avaliar o ganho preditivo adicional da faixa.</p></section>
{''.join(sections)}<section><h2>Limitações</h2><p>{escape(LIMITS)}</p><p class="provenance">{escape(provenance)}</p><p><a href="relatorio.md">Relatório completo e padrões de treino</a> · <a href="metricas.csv">Métricas CSV</a> · <a href="teste_por_faixa.csv">Teste por faixa</a> · <a href="padroes_treino.csv">Padrões CSV</a> · <a href="resultados.json">Resultados JSON</a></p><p>Fonte: <a href="https://doi.org/10.24432/C5TG7T">Cortez (2008), Student Performance/UCI</a> · <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>.</p></section></main></body></html>"""
    (output / "relatorio.html").write_text(html, encoding="utf-8")


def run_modeling(source, output):
    source, output = Path(source), Path(output)
    # Evitar sobrescrever entradas, dados brutos ou outras etapas do projeto.
    for protected in (source, ROOT / "data", ROOT / "scripts", ROOT / "tests", ROOT / "docs", ROOT / "reports/eda"):
        if output.resolve().is_relative_to(protected.resolve()) or protected.resolve().is_relative_to(output.resolve()):
            raise ValueError("Guarde a modelagem fora das pastas protegidas de entrada e das outras etapas.")
    paths = [source / name for name in ("base_tratada.csv", "qualidade.json", "resumo_faixas.csv")]
    rows = load_base(paths[0])
    quality = json.loads(paths[1].read_text(encoding="utf-8"))
    reconcile(rows, quality, paths[2])
    if not quality.get("pronta_para_analise") or any(row["sinalizacoes"] for row in rows):
        raise ValueError("Resolva as pendências do ETL antes de ajustar os modelos.")
    import joblib
    import numpy as np
    import scipy
    import sklearn
    os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mpl-cache"))
    import matplotlib
    result = {"versao_modelagem": "1.0.0", "executado_em_utc": datetime.now(timezone.utc).isoformat(),
              "semente": SEED, "fracao_teste": .2, "dobras_cv": 5, "alvo": "G3", "escala_notas": [0, 20],
              "metodo": METHOD, "limites": LIMITS,
              "entradas_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
              "ambiente": {"python": platform.python_version(), "numpy": np.__version__,
                           "scipy": scipy.__version__, "scikit_learn": sklearn.__version__,
                           "matplotlib": matplotlib.__version__, "joblib": joblib.__version__}, "disciplinas": {}}
    fitted = {}
    for subject, slug in SLUGS.items():
        group = [row for row in rows if row["disciplina"] == subject]
        train, test, folds = split_data(group)
        def partition_hash(indices):
            return hashlib.sha256(json.dumps([group[int(i)]["registro_origem"] for i in indices]).encode()).hexdigest()
        split = {"treino": len(train), "teste": len(test),
                 "treino_sha256": partition_hash(train), "teste_sha256": partition_hash(test),
                 "zeros_treino": sum(group[int(i)]["G3"] == 0 for i in train),
                 "zeros_teste": sum(group[int(i)]["G3"] == 0 for i in test),
                 "faixas_treino": dict(sorted(Counter(str(group[int(i)]["studytime"]) for i in train).items())),
                 "faixas_teste": dict(sorted(Counter(str(group[int(i)]["studytime"]) for i in test).items()))}
        data = {"particao": split, "mineracao_treino": mine_training([group[int(i)] for i in train]), "cenarios": {}}
        for scenario, (_, fields) in SCENARIOS.items():
            data["cenarios"][scenario], chosen = fit_scenario(group, fields, train, test, folds)
            fitted[f"{slug}_{scenario}"] = chosen, fields
        result["disciplinas"][subject] = data
    output.mkdir(parents=True, exist_ok=True)
    folder = output / "modelos"
    folder.mkdir(exist_ok=True)
    # Arquivos binários são locais; os agregados e parâmetros ficam versionáveis.
    (folder / ".gitignore").write_text("*.joblib\n", encoding="utf-8")
    for name, (model, fields) in fitted.items():
        joblib.dump(model, folder / f"{name}.joblib", compress=3)
        (folder / f"{name}.txt").write_text(model_summary(model, fields), encoding="utf-8")
    metric_rows, pattern_rows, band_rows = [], [], []
    for subject, data in result["disciplinas"].items():
        pattern_rows.extend({"disciplina": subject, **band} for band in data["mineracao_treino"]["faixas"])
        for scenario, item in data["cenarios"].items():
            metric_rows.extend({"disciplina": subject, "cenario": scenario, **{key: model[key] for key in METRIC_FIELDS[2:]}} for model in item["modelos"])
            band_rows.extend({"disciplina": subject, "cenario": scenario, "modelo": item["selecionado"], **band} for band in item["teste_por_faixa"])
    def save_csv(name, records):
        values = [{key: Decimal(f"{value:.6f}") if isinstance(value, float) else value for key, value in row.items()} for row in records]
        write_csv(output / name, tuple(records[0]), values)
    save_csv("metricas.csv", metric_rows)
    save_csv("padroes_treino.csv", pattern_rows)
    save_csv("teste_por_faixa.csv", band_rows)
    (output / "resultados.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    charts(result, output)
    reports(result, output)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=ROOT / "data/processed/uci")
    parser.add_argument("--saida", type=Path, default=ROOT / "reports/modelagem")
    args = parser.parse_args()
    try:
        result = run_modeling(args.entrada, args.saida)
    except ModuleNotFoundError as exc:
        print(f"Dependência ausente ({exc.name}). Instale: python -m pip install -r requirements-modelagem.txt", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError, csv.Error, InvalidOperation) as exc:
        print(f"Falha na modelagem: {exc}", file=sys.stderr)
        return 1
    for subject, data in result["disciplinas"].items():
        print(subject + ": " + conclusions(subject, data)[0])
    print(f"Relatório: {args.saida / 'relatorio.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
