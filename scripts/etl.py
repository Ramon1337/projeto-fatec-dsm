"""ETL do Student Performance/UCI. Python 3.10+, sem dependências externas."""

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import io
import json
from pathlib import Path
import re
import sys


VERSION = "2.0.0"
SOURCE_URL = "https://archive.ics.uci.edu/dataset/320/student+performance"
DOI = "https://doi.org/10.24432/C5TG7T"
ROOT = Path(__file__).resolve().parents[1]
SUBJECTS = {"student-por.csv": "Português", "student-mat.csv": "Matemática"}
# Rótulos da fonte, não limites inferidos de horas individuais.
BANDS = {1: "Menos de 2 horas", 2: "2 a 5 horas", 3: "5 a 10 horas", 4: "Mais de 10 horas"}
SOURCE_FIELDS = tuple("school sex age address famsize Pstatus Medu Fedu Mjob Fjob reason guardian traveltime studytime failures schoolsup famsup paid activities nursery higher internet romantic famrel freetime goout Dalc Walc health absences G1 G2 G3".split())
NUMERIC_FIELDS = ("studytime", "G1", "G2", "G3")
BASE_FIELDS = ("disciplina", "registro_origem", "studytime", "faixa_estudo", "G1", "G2", "G3", "nota_final_0_10", "sinalizacoes")
SUMMARY_FIELDS = ("disciplina", "studytime", "faixa_estudo", "quantidade", "media_nota_final_0_20", "media_nota_final_0_10", "notas_finais_zero")
ISSUE_FIELDS = ("disciplina", "registro_origem", "tipo", "campo", "motivo", "registro_relacionado")
OUTPUT_NAMES = ("base_tratada.csv", "resumo_faixas.csv", "ocorrencias.csv", "qualidade.json")


def parse_integer(value, lower, upper):
    text = value.strip()
    if not text:
        raise ValueError("ausente")
    if not re.fullmatch(r"[0-9]{1,3}", text):
        raise ValueError("formato_inteiro_invalido")
    result = int(text)
    if not lower <= result <= upper:
        raise ValueError("fora_do_dominio")
    return result


def mean(values):
    if not values:
        return None
    return (sum(Decimal(value) for value in values) / len(values)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def csv_value(value):
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return format(value, "f").replace(".", ",")
    return value


def write_csv(path, fields, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";", lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: csv_value(row.get(field)) for field in fields} for row in rows)


def extract(path):
    raw = path.read_bytes()
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""), delimiter=";", strict=True)
    headers = reader.fieldnames or []
    if len(headers) != len(SOURCE_FIELDS) or set(headers) != set(SOURCE_FIELDS):
        raise ValueError("Cabeçalho incompatível com as 33 colunas oficiais da UCI.")
    return raw, list(reader)


def run_etl(source_dir, output):
    source_dir, output = Path(source_dir), Path(output)
    if output.resolve() == source_dir.resolve() or output.resolve().is_relative_to(source_dir.resolve()):
        raise ValueError("A saída deve ficar fora da pasta bruta, preservando sua integridade.")
    # Extrair ambos antes de gerar saídas: entrada ausente/incompatível falha integralmente.
    inputs = {filename: extract(source_dir / filename) for filename in SUBJECTS}
    accepted, issues, subjects = [], [], {}
    for filename, subject in SUBJECTS.items():
        raw, records = inputs[filename]
        rejected, seen, subject_rows = 0, {}, []
        for record_number, row in enumerate(records, start=1):
            errors, cleaned = [], {}
            if None in row or any(value is None for value in row.values()):
                errors.append(("registro", "quantidade_de_colunas_invalida"))
            for field in NUMERIC_FIELDS:
                lower, upper = (1, 4) if field == "studytime" else (0, 20)
                try:
                    cleaned[field] = parse_integer(row.get(field) or "", lower, upper)
                except ValueError as exc:
                    errors.append((field, str(exc)))
            if errors:
                rejected += 1
                issues.extend({"disciplina": subject, "registro_origem": record_number,
                               "tipo": "exclusao", "campo": field, "motivo": reason,
                               "registro_relacionado": ""} for field, reason in errors)
                continue
            # Igualdade apenas nas variáveis analíticas não é duplicidade.
            key = tuple((row[field] or "").strip() for field in SOURCE_FIELDS)
            flags = []
            if key in seen:
                flags.append("linha_completa_repetida")
                issues.append({"disciplina": subject, "registro_origem": record_number,
                               "tipo": "revisao", "campo": "registro", "motivo": flags[-1],
                               "registro_relacionado": seen[key]})
            else:
                seen[key] = record_number
            treated = {"disciplina": subject, "registro_origem": record_number, **cleaned,
                       "faixa_estudo": BANDS[cleaned["studytime"]],
                       "nota_final_0_10": Decimal(cleaned["G3"]) / 2,
                       "sinalizacoes": " | ".join(flags)}
            subject_rows.append(treated)
        accepted.extend(subject_rows)
        subject_issues = [issue for issue in issues if issue["disciplina"] == subject]
        review_count = len({issue["registro_origem"] for issue in subject_issues if issue["tipo"] == "revisao"})
        average = mean([row["G3"] for row in subject_rows])
        subjects[subject] = {
            "arquivo": filename, "entrada_sha256": hashlib.sha256(raw).hexdigest(),
            "total_recebidas": len(records), "total_validas": len(subject_rows), "total_excluidas": rejected,
            "registros_para_revisao": review_count,
            "ocorrencias_por_motivo": dict(Counter(issue["motivo"] for issue in subject_issues)),
            "media_nota_final_0_20": float(average) if average is not None else None,
            "notas_finais_zero": sum(row["G3"] == 0 for row in subject_rows),
            "pronta_para_analise": bool(subject_rows) and review_count == 0,
        }
    summary = []
    for subject in SUBJECTS.values():
        for code, band in BANDS.items():
            group = [row for row in accepted if row["disciplina"] == subject and row["studytime"] == code]
            summary.append({"disciplina": subject, "studytime": code, "faixa_estudo": band,
                            "quantidade": len(group), "media_nota_final_0_20": mean([row["G3"] for row in group]),
                            "media_nota_final_0_10": mean([row["nota_final_0_10"] for row in group]),
                            "notas_finais_zero": sum(row["G3"] == 0 for row in group)})
    report = {
        "versao_etl": VERSION, "executado_em_utc": datetime.now(timezone.utc).isoformat(),
        "origem": "UCI Student Performance — dados secundários reais",
        "fonte": SOURCE_URL, "doi": DOI, "licenca": "CC BY 4.0",
        "disciplina_principal": "Português", "unidade_observacao": "registro de aluno por disciplina",
        "disciplinas": subjects, "total_registros_validos": len(accepted), "total_alunos_unicos": None,
        "sobreposicao": "Há alunos nos dois arquivos; analisar separadamente, sem somar como pessoas distintas.",
        "faixas_studytime": BANDS, "escala_original_notas": [0, 20],
        "conversao_opcional": "nota_final_0_10 = G3 / 2; G3 original preservado",
        "politica_zeros": "G3=0 é válido e mantido; não é interpretado automaticamente como ausência",
        "politica_duplicidades": "linhas completas repetidas são sinalizadas e mantidas para revisão",
        "escopo_validacao": "estrutura de 33 colunas e domínio de studytime/G1/G2/G3; demais atributos não carregados",
        "pronta_para_analise": all(subject["pronta_para_analise"] for subject in subjects.values()),
    }
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / OUTPUT_NAMES[0], BASE_FIELDS, accepted)
    write_csv(output / OUTPUT_NAMES[1], SUMMARY_FIELDS, summary)
    write_csv(output / OUTPUT_NAMES[2], ISSUE_FIELDS, issues)
    (output / OUTPUT_NAMES[3]).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=ROOT / "data/raw/uci")
    parser.add_argument("--saida", type=Path, default=ROOT / "data/processed/uci")
    args = parser.parse_args()
    try:
        report = run_etl(args.entrada, args.saida)
    except (OSError, ValueError, csv.Error):
        print("Falha no ETL. Confira os dois CSVs oficiais e a estrutura de 33 colunas; consulte docs/coleta-tratamento-etl.md.", file=sys.stderr)
        return 1
    for subject, quality in report["disciplinas"].items():
        print(f"{subject}: {quality['total_recebidas']} recebidas, {quality['total_validas']} válidas, {quality['total_excluidas']} excluídas, {quality['registros_para_revisao']} para revisão.")
    print(f"Saída: {args.saida}. São registros por disciplina, não uma contagem de alunos únicos.")
    return 0 if all(subject["total_validas"] for subject in report["disciplinas"].values()) else 2


if __name__ == "__main__":
    sys.exit(main())
