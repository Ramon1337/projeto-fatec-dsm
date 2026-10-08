"""EDA reproduzível da base tratada UCI, com relatórios e gráficos por disciplina."""

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
from html import escape
import json
import math
import os
from pathlib import Path
import statistics
import sys

try:
    from scripts.etl import BANDS, BASE_FIELDS, SUBJECTS, parse_integer, write_csv
except ModuleNotFoundError:  # Execução direta: python scripts/eda.py
    from etl import BANDS, BASE_FIELDS, SUBJECTS, parse_integer, write_csv

ROOT = Path(__file__).resolve().parents[1]
SLUGS = {"Português": "portugues", "Matemática": "matematica"}
COLORS = ["#155e75", "#217e91", "#46a1a0", "#85c3b8"]
STAT_FIELDS = ("disciplina", "studytime", "faixa_estudo", "variavel", "quantidade",
               "media", "mediana", "desvio_padrao_amostral", "minimo", "q1", "q3",
               "maximo", "notas_zero", "atipicos_iqr")


def percentile(values, proportion):
    """Quantil por interpolação linear, índice (n-1)*p (tipo 7)."""
    if not 0 <= proportion <= 1:
        raise ValueError("Proporção fora de 0 a 1.")
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * proportion
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def describe(values):
    if not values:
        return dict.fromkeys(STAT_FIELDS[5:], None) | {"quantidade": 0, "notas_zero": 0, "atipicos_iqr": 0}
    q1, q3 = percentile(values, .25), percentile(values, .75)
    iqr = q3 - q1
    return {"quantidade": len(values), "media": statistics.mean(values),
            "mediana": statistics.median(values),
            "desvio_padrao_amostral": statistics.stdev(values) if len(values) > 1 else None,
            "minimo": min(values), "q1": q1, "q3": q3, "maximo": max(values),
            "notas_zero": values.count(0),
            "atipicos_iqr": sum(value < q1 - 1.5 * iqr or value > q3 + 1.5 * iqr for value in values)}


def ranks(values):
    """Postos médios nos empates, preservando a ordem das observações."""
    counts = Counter(values)
    position, mapping = 1, {}
    for value in sorted(counts):
        mapping[value] = position + (counts[value] - 1) / 2
        position += counts[value]
    return [mapping[value] for value in values]


def spearman(x, y):
    if len(x) != len(y):
        raise ValueError("Vetores de tamanhos diferentes.")
    if len(x) < 2 or len(set(x)) < 2 or len(set(y)) < 2:
        return None
    rx, ry = ranks(x), ranks(y)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    numerator = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    denominator = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return max(-1.0, min(1.0, numerator / denominator))


def load_base(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";", strict=True)
        if tuple(reader.fieldnames or []) != BASE_FIELDS:
            raise ValueError("Cabeçalho incompatível com a base tratada; execute o ETL.")
        rows, seen = [], set()
        for line, row in enumerate(reader, 2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Quantidade de campos inválida na linha {line}.")
            if row["disciplina"] not in SLUGS:
                raise ValueError(f"Disciplina inválida na linha {line}.")
            for field in ("studytime", "G1", "G2", "G3", "registro_origem"):
                lower, upper = (1, 4) if field == "studytime" else (0, 20)
                if field == "registro_origem":
                    # O identificador é uma posição; não é uma variável analítica.
                    if not row[field].isascii() or not row[field].isdigit() or int(row[field]) < 1:
                        raise ValueError(f"Posição de origem inválida na linha {line}.")
                    row[field] = int(row[field])
                else:
                    row[field] = parse_integer(row[field], lower, upper)
            if row["faixa_estudo"] != BANDS[row["studytime"]]:
                raise ValueError(f"Faixa inconsistente na linha {line}.")
            if Decimal(row["nota_final_0_10"].replace(",", ".")) != Decimal(row["G3"]) / 2:
                raise ValueError(f"Conversão da nota inconsistente na linha {line}.")
            key = row["disciplina"], row["registro_origem"]
            if key in seen:
                raise ValueError(f"Posição repetida dentro da disciplina na linha {line}.")
            seen.add(key)
            rows.append(row)
    if any(not any(row["disciplina"] == subject for row in rows) for subject in SLUGS):
        raise ValueError("As duas disciplinas precisam ter registros válidos.")
    return rows


def analyze(rows):
    subjects, correlations = {}, []
    for subject in SUBJECTS.values():
        group = [row for row in rows if row["disciplina"] == subject]
        total = {field: describe([row[field] for row in group]) for field in ("G1", "G2", "G3")}
        bands = [{"studytime": code, "faixa_estudo": band,
                  **describe([row["G3"] for row in group if row["studytime"] == code])}
                 for code, band in BANDS.items()]
        subjects[subject] = {"notas": total, "faixas": bands,
                             "registros_sinalizados": sum(bool(row["sinalizacoes"]) for row in group)}
        for x, y in (("studytime", "G3"), ("G1", "G3"), ("G2", "G3")):
            correlations.append({"disciplina": subject, "variavel_x": x, "variavel_y": y,
                                 "quantidade": len(group),
                                 "rho_spearman": spearman([row[x] for row in group], [row[y] for row in group])})
    return {"disciplinas": subjects, "correlacoes": correlations}


def reconcile(rows, quality, summary_path):
    """Confronta a base com os dois produtos do ETL antes de escrever resultados."""
    if quality.get("total_registros_validos") != len(rows):
        raise ValueError("Contagem da base diverge do relatório de qualidade.")
    for subject in SLUGS:
        group = [row for row in rows if row["disciplina"] == subject]
        item = quality["disciplinas"][subject]
        if (item["total_validas"] != len(group)
                or item["notas_finais_zero"] != sum(row["G3"] == 0 for row in group)
                or abs(item["media_nota_final_0_20"] - statistics.mean(row["G3"] for row in group)) > .000051
                or item["registros_para_revisao"] != sum(bool(row["sinalizacoes"]) for row in group)):
            raise ValueError(f"Base e qualidade divergem em {subject}.")
    with summary_path.open(encoding="utf-8-sig", newline="") as handle:
        summary = list(csv.DictReader(handle, delimiter=";", strict=True))
    keys = [(row["disciplina"], int(row["studytime"])) for row in summary]
    if len(keys) != 8 or set(keys) != {(subject, code) for subject in SLUGS for code in BANDS}:
        raise ValueError("Resumo de faixas incompatível com as oito categorias.")
    for item in summary:
        group = [row for row in rows if (row["disciplina"], row["studytime"]) == (item["disciplina"], int(item["studytime"]))]
        expected = statistics.mean(row["G3"] for row in group) if group else None
        observed = float(item["media_nota_final_0_20"].replace(",", ".")) if item["media_nota_final_0_20"] else None
        if (int(item["quantidade"]) != len(group)
                or int(item["notas_finais_zero"]) != sum(row["G3"] == 0 for row in group)
                or (expected is None) != (observed is None)
                or (expected is not None and (not math.isfinite(observed) or abs(expected - observed) > .000051))):
            raise ValueError("Resumo de faixas diverge da base tratada.")


def fmt(value, digits=2):
    return "—" if value is None else f"{value:.{digits}f}".replace(".", ",")


def findings(subject, result):
    data = result["disciplinas"][subject]
    bands = [band for band in data["faixas"] if band["quantidade"]]
    best = max(bands, key=lambda band: band["media"])
    rho = next(item["rho_spearman"] for item in result["correlacoes"]
               if item["disciplina"] == subject and item["variavel_x"] == "studytime")
    text = [f"{subject}: {data['notas']['G3']['quantidade']} registros; média final {fmt(data['notas']['G3']['media'])} e mediana {fmt(data['notas']['G3']['mediana'])}, na escala 0–20.",
            f"A maior média observada está na faixa {best['faixa_estudo'].lower()}: {fmt(best['media'])} (n={best['quantidade']})."]
    if len(bands) == 4:
        direction = "superior" if bands[3]["media"] > bands[2]["media"] else "inferior" if bands[3]["media"] < bands[2]["media"] else "igual"
        pattern = "As médias crescem nas quatro faixas." if all(a["media"] < b["media"] for a, b in zip(bands, bands[1:])) else "Não há crescimento contínuo das quatro médias."
        text.append(f"A média na faixa mais de 10 horas é {direction} à da faixa 5 a 10 horas. {pattern}")
        text.append(f"A diferença entre mais de 10 horas e menos de 2 horas é {fmt(bands[3]['media'] - bands[0]['media'])} pontos. Os grupos têm tamanhos diferentes ({', '.join(str(b['quantidade']) for b in bands)}).")
    text.append(f"Spearman entre a categoria ordinal de estudo e G3: {fmt(rho, 3)}. É uma associação descritiva por postos, sem teste de significância e sem interpretação causal.")
    text.append(f"Foram mantidas {data['notas']['G3']['notas_zero']} notas finais zero. A regra de 1,5 × IQR sinaliza {data['notas']['G3']['atipicos_iqr']} valores atípicos na distribuição geral; eles permanecem na análise.")
    return text


def charts(rows, result, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "svg.fonttype": "none", "svg.hashsalt": "uci-eda"})
    folder = output / "graficos"
    folder.mkdir(exist_ok=True)
    for subject, slug in SLUGS.items():
        data = result["disciplinas"][subject]
        group = [row for row in rows if row["disciplina"] == subject]
        labels = ["Menos de\n2 horas", "2 a 5\nhoras", "5 a 10\nhoras", "Mais de\n10 horas"]
        for kind in ("medias", "boxplot", "distribuicao", "quantidades"):
            fig, ax = plt.subplots(figsize=(9, 5.5))
            ax.set_axisbelow(True)
            ax.grid(axis="y", color="#e2e8f0")
            ax.set_title(subject + " · " + {"medias": "nota final média por faixa de estudo",
                         "boxplot": "dispersão da nota final por faixa de estudo",
                         "distribuicao": "distribuição das notas finais",
                         "quantidades": "registros por faixa de estudo"}[kind], pad=20, fontweight="bold")
            if kind == "medias":
                heights = [band["media"] if band["media"] is not None else 0 for band in data["faixas"]]
                ax.bar(range(4), heights, color=COLORS, width=.6)
                for i, band in enumerate(data["faixas"]):
                    ax.text(i, heights[i] + .4, f"{fmt(band['media'])}\nn={band['quantidade']}", ha="center")
                ax.axhline(data["notas"]["G3"]["media"], color="#b45309", linestyle="--",
                           label="Média da disciplina: " + fmt(data["notas"]["G3"]["media"]))
                ax.legend(loc="upper left", frameon=False, fontsize=10)
            elif kind == "boxplot":
                nonempty = [(i, [row["G3"] for row in group if row["studytime"] == i + 1]) for i in range(4)]
                nonempty = [(i, values) for i, values in nonempty if values]
                boxes = ax.boxplot([values for _, values in nonempty], positions=[i for i, _ in nonempty],
                                   widths=.5, patch_artist=True, whis=1.5,
                                   medianprops={"color": "#0f172a", "linewidth": 2},
                                   flierprops={"marker": "o", "markersize": 4, "alpha": .4})
                for patch, (i, _) in zip(boxes["boxes"], nonempty):
                    patch.set_facecolor(COLORS[i])
                for i, band in enumerate(data["faixas"]):
                    ax.text(i, 21, f"n={band['quantidade']}", ha="center", fontsize=10)
            elif kind == "distribuicao":
                frequencies = Counter(row["G3"] for row in group)
                ax.bar(range(21), [frequencies[grade] for grade in range(21)], color=COLORS[0], width=.85)
                ax.set_xticks(range(0, 21, 2))
                ax.set_xlabel("Nota final G3 (0–20); notas zero incluídas")
                ax.set_ylabel("Quantidade de registros")
                ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            else:
                counts = [band["quantidade"] for band in data["faixas"]]
                ax.bar(range(4), counts, color=COLORS, width=.6)
                for i, count in enumerate(counts):
                    ax.text(i, count + max(counts) * .025, f"{count} ({fmt(100 * count / len(group), 1)}%)", ha="center")
                ax.set_ylim(0, max(counts) * 1.22)
                ax.set_ylabel("Quantidade de registros")
                ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            if kind in ("medias", "boxplot"):
                ax.set_ylim(-.5 if kind == "boxplot" else 0, 22)
                ax.set_yticks(range(0, 21, 5))
                ax.set_ylabel("Nota final G3 · escala original 0–20")
            if kind != "distribuicao":
                ax.set_xticks(range(4), labels)
                ax.set_xlim(-.6, 3.6)
                ax.set_xlabel("Faixa de estudo semanal (categorias da fonte)")
            fig.text(.02, .015, "Fonte: Cortez (2008), Student Performance/UCI · CC BY 4.0 · Análise descritiva", fontsize=9, color="#475569")
            fig.tight_layout(rect=(0, .045, 1, 1))
            for extension in ("svg", "png"):
                fig.savefig(folder / f"{slug}_{kind}.{extension}", dpi=160,
                            metadata={"Date": None} if extension == "svg" else None)
            plt.close(fig)


def reports(result, output):
    introduction = ("Português é a análise principal; Matemática é uma comparação separada. "
                    "A unidade é um registro de aluno por disciplina. Há alunos nos dois arquivos; "
                    "as contagens não representam pessoas distintas somadas.")
    methodology = ("Estatísticas calculadas diretamente da base tratada, sem imputação ou remoção de zeros. "
                   "Quartis por interpolação linear (tipo 7); desvio-padrão amostral (n−1), indisponível para n<2. "
                   "Boxplots: caixa Q1–Q3, linha da mediana, bigodes até as observações dentro de 1,5 × IQR "
                   "e pontos além dos bigodes. Pontos sobrepostos podem representar vários registros. "
                   "Atípicos são sinais para inspeção, não erros nem justificativa automática para exclusão. "
                   "Os limites IQR são recalculados por grupo; a soma dos atípicos por faixa pode diferir do total da disciplina. "
                   "Spearman usa postos médios nos empates e fica indisponível para variável constante. "
                   "Os códigos de estudo não são horas exatas ou intervalos iguais.")
    limitations = ("Dados observacionais históricos de duas escolas portuguesas. "
                   "Os grupos têm tamanhos desiguais, e a faixa mais de 10 horas é pequena. "
                   "Não foram controlados outros fatores. Não se estimaram p-valores ou intervalos de confiança. "
                   "As diferenças não demonstram causalidade, significância estatística ou representatividade da FATEC.")
    markdown = ["# EDA e visualização — Estudo e desempenho escolar", introduction]
    sections = []
    for subject, slug in SLUGS.items():
        data = result["disciplinas"][subject]
        g3 = data["notas"]["G3"]
        markdown += [f"## {subject}", *findings(subject, result),
                     "| Faixa | n | Média G3 | Mediana | DP amostral | Q1 | Q3 | Zero | Atípicos IQR |",
                     "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
        cells = []
        for band in data["faixas"]:
            values = [band["faixa_estudo"], str(band["quantidade"]), fmt(band["media"]),
                      fmt(band["mediana"]), fmt(band["desvio_padrao_amostral"]),
                      fmt(band["q1"]), fmt(band["q3"]), str(band["notas_zero"]), str(band["atipicos_iqr"])]
            markdown.append("| " + " | ".join(values) + " |")
            cells.append("<tr>" + "".join(f"<td>{escape(value)}</td>" for value in values) + "</tr>")
        cards = "".join(f'<div class="card"><span>{label}</span><strong>{value}</strong></div>' for label, value in
                        (("Registros", g3["quantidade"]), ("Média G3 · 0–20", fmt(g3["media"])),
                         ("Mediana G3", fmt(g3["mediana"])), ("DP amostral", fmt(g3["desvio_padrao_amostral"]))))
        figures = []
        for kind, caption in (("medias", "Médias e tamanho de cada faixa"),
                              ("boxplot", "Dispersão, mediana e valores atípicos"),
                              ("distribuicao", "Frequência de cada nota final"),
                              ("quantidades", "Composição da amostra por faixa")):
            path = f"graficos/{slug}_{kind}.svg"
            markdown += [f"![{subject}: {caption}]({path})"]
            figures.append(f'<figure><img src="{path}" alt="{escape(subject + ": " + caption)}"><figcaption>{caption} · <a href="graficos/{slug}_{kind}.png">PNG</a> / <a href="{path}">SVG</a></figcaption></figure>')
        bullets = "".join(f"<li>{escape(line)}</li>" for line in findings(subject, result))
        sections.append(f'<section id="{slug}"><p class="eyebrow">{"Análise principal" if slug == "portugues" else "Comparação separada"}</p><h2>{subject}</h2><div class="cards">{cards}</div><ul>{bullets}</ul><div class="table-scroll"><table><caption>Notas finais por faixa de estudo · escala 0–20</caption><thead><tr>'
                        + "".join(f'<th scope="col">{label}</th>' for label in ("Faixa", "n", "Média", "Mediana", "DP", "Q1", "Q3", "Zero", "Atípicos IQR"))
                        + '</tr></thead><tbody>' + "".join(cells) + '</tbody></table></div><div class="figures">' + "".join(figures) + '</div></section>')
    correlation_rows = []
    markdown += ["## Associações por postos", "| Disciplina | Variáveis | n | Spearman |", "|---|---|---:|---:|"]
    for item in result["correlacoes"]:
        values = [item["disciplina"], item["variavel_x"] + " × " + item["variavel_y"], str(item["quantidade"]), fmt(item["rho_spearman"], 3)]
        markdown.append("| " + " | ".join(values) + " |")
        correlation_rows.append("<tr>" + "".join(f"<td>{escape(value)}</td>" for value in values) + "</tr>")
    quality = result["qualidade"]
    quality_text = f"Reconciliação com o ETL aprovada. Campos analíticos ausentes na base: 0. Registros sinalizados: {sum(d['registros_sinalizados'] for d in result['disciplinas'].values())}. Exclusões registradas no ETL: {sum(d['total_excluidas'] for d in quality['disciplinas'].values())}."
    if not quality["pronta_para_analise"]:
        quality_text += " RESULTADOS PROVISÓRIOS: revisar as ocorrências do ETL antes de concluir."
    provenance = (f"SHA-256 da base tratada: {result['entradas_sha256']['base_tratada.csv']}. "
                  f"ETL registrado em UTC: {quality['executado_em_utc']}. EDA em UTC: {result['executado_em_utc']}.")
    source = 'Fonte: <a href="https://doi.org/10.24432/C5TG7T">Cortez (2008), Student Performance/UCI</a>. Licença: <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. Resumos e gráficos derivados pelo projeto.'
    markdown += ["## Qualidade e rastreabilidade", quality_text, provenance, "## Metodologia", methodology,
                 "## Limitações", limitations,
                 "Fonte: [Cortez (2008), Student Performance/UCI](https://doi.org/10.24432/C5TG7T). Licença: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Resumos e gráficos derivados pelo projeto."]
    markdown_text = ""
    previous = ""
    for block in markdown:
        separator = "\n" if previous.startswith("|") and block.startswith("|") else "\n\n"
        markdown_text += (separator if markdown_text else "") + block
        previous = block
    (output / "relatorio.md").write_text(markdown_text + "\n", encoding="utf-8")
    html = f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>EDA · Estudo e desempenho escolar</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#f3f6f7;color:#18313b;font:16px/1.6 system-ui,sans-serif}}
header{{background:#123b48;color:white;padding:48px max(24px,calc((100vw - 1160px)/2))}}h1{{font-size:clamp(28px,4vw,44px);line-height:1.15;margin:12px 0 20px;max-width:900px}}
header p{{max-width:950px;color:#d6e7eb}}.eyebrow{{font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase}}nav{{display:flex;gap:20px;flex-wrap:wrap}}nav a{{color:#fff}}
main{{max-width:1208px;margin:auto;padding:28px 24px}}section{{background:white;border:1px solid #dbe5e8;border-radius:16px;padding:28px;margin:0 0 28px;scroll-margin:20px}}
h2{{font-size:30px;margin:8px 0 20px}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.card{{padding:18px;background:#edf5f5;border-radius:10px}}
.card span{{display:block;color:#4d6670;font-size:13px}}.card strong{{font-size:30px}}li{{margin:8px 0}}.table-scroll{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}caption{{text-align:left;font-weight:600;padding:14px 0}}th,td{{padding:11px;border-bottom:1px solid #dbe5e8;text-align:right;white-space:nowrap}}th:first-child,td:first-child{{text-align:left}}th{{background:#edf5f5}}
.figures{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:24px}}figure{{margin:0;border:1px solid #dbe5e8;border-radius:10px;overflow:hidden}}img{{display:block;width:100%;height:auto}}figcaption{{padding:10px 16px;background:#f5f8f9;font-size:13px}}a{{color:#155e75}}.provenance{{font-size:12px;overflow-wrap:anywhere;color:#4d6670}}footer{{padding:0 10px 30px;font-size:13px}}
@media(max-width:800px){{.figures{{grid-template-columns:1fr}}.cards{{grid-template-columns:repeat(2,1fr)}}section{{padding:18px}}main{{padding:16px}}}}@media print{{body{{background:white}}header{{padding:20px}}section{{border:0;padding:10px}}figure,.cards,table{{break-inside:avoid}}nav{{display:none}}}}
</style></head><body><header><div class="eyebrow">Projeto FATEC DSM · Análise exploratória</div><h1>Tempo de estudo e desempenho escolar</h1><p>{introduction}</p><nav aria-label="Seções"><a href="#portugues">Português</a><a href="#matematica">Matemática</a><a href="#metodo">Método e limites</a></nav></header>
<main>{''.join(sections)}<section><h2>Associações por postos</h2><p>Spearman mede associação monotônica. studytime é ordinal. G1/G2 são notas dos períodos anteriores; sua associação com G3 não prova efeito do estudo.</p><div class="table-scroll"><table><thead><tr><th>Disciplina</th><th>Variáveis</th><th>n</th><th>Spearman</th></tr></thead><tbody>{''.join(correlation_rows)}</tbody></table></div></section>
<section id="metodo"><h2>Método, qualidade e limites</h2><p>{escape(methodology)}</p><p>{escape(quality_text)}</p><p>{escape(limitations)}</p><p class="provenance">{escape(provenance)}</p><p><a href="estatisticas.csv">Estatísticas CSV</a> · <a href="correlacoes.csv">Correlações CSV</a> · <a href="indicadores.json">Indicadores JSON</a> · <a href="relatorio.md">Relatório Markdown</a></p></section><footer>{source}</footer></main></body></html>'''
    (output / "relatorio.html").write_text(html, encoding="utf-8")


def run_eda(source, output):
    source, output = Path(source), Path(output)
    if output.resolve().is_relative_to(source.resolve()) or output.resolve().is_relative_to((ROOT / "data/raw").resolve()):
        raise ValueError("Guarde a EDA fora das pastas de dados de entrada.")
    paths = [source / name for name in ("base_tratada.csv", "qualidade.json", "resumo_faixas.csv")]
    rows = load_base(paths[0])
    quality = json.loads(paths[1].read_text(encoding="utf-8"))
    reconcile(rows, quality, paths[2])
    result = analyze(rows)
    result.update(versao_eda="1.0.0", executado_em_utc=datetime.now(timezone.utc).isoformat(),
                  entradas_sha256={path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
                  qualidade=quality, escala_notas=[0, 20], metodo_quartis="tipo 7, interpolação linear",
                  metodo_correlacao="Spearman com postos médios nos empates; sem inferência estatística")
    # Importar antes de criar saídas para fornecer uma falha clara se faltar Matplotlib.
    os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mpl-cache"))
    import matplotlib  # noqa: F401
    output.mkdir(parents=True, exist_ok=True)
    charts(rows, result, output)
    stats = []
    for subject, data in result["disciplinas"].items():
        stats.extend({"disciplina": subject, "studytime": "", "faixa_estudo": "Todas", "variavel": variable, **values}
                     for variable, values in data["notas"].items())
        stats.extend({"disciplina": subject, "variavel": "G3", **band} for band in data["faixas"])
    def csv_rows(items):
        return [{key: Decimal(f"{value:.6f}") if isinstance(value, float) else value for key, value in item.items()} for item in items]
    write_csv(output / "estatisticas.csv", STAT_FIELDS, csv_rows(stats))
    write_csv(output / "correlacoes.csv", ("disciplina", "variavel_x", "variavel_y", "quantidade", "rho_spearman"), csv_rows(result["correlacoes"]))
    (output / "indicadores.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    reports(result, output)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=ROOT / "data/processed/uci", help="Pasta com os três produtos do ETL.")
    parser.add_argument("--saida", type=Path, default=ROOT / "reports/eda")
    args = parser.parse_args()
    try:
        result = run_eda(args.entrada, args.saida)
    except ModuleNotFoundError:
        print("Instale as dependências: python -m pip install -r requirements-eda.txt", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError, csv.Error, InvalidOperation) as exc:
        print(f"Falha na EDA: {exc}", file=sys.stderr)
        return 1
    for subject in SLUGS:
        print(findings(subject, result)[0])
    print(f"Relatório: {args.saida / 'relatorio.html'}. Gerados oito gráficos em SVG e PNG.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
