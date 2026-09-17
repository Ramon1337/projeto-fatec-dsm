import csv
import hashlib
import io
import json
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
import uuid
from zipfile import ZipFile

from scripts.coletar_uci import collect, DOWNLOAD_URL, FILES, read_package
from scripts.etl import run_etl, SOURCE_FIELDS


ROOT = Path(__file__).resolve().parents[1]


def observation(studytime="1", grade="10", context="contexto-a", **changes):
    row = dict.fromkeys(SOURCE_FIELDS, context)
    row.update(studytime=studytime, G1="10", G2="11", G3=grade)
    row.update(changes)
    return row


def csv_bytes(rows, fields=SOURCE_FIELDS):
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue().encode("utf-8")


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        temporary_root = (ROOT / ".test-tmp").resolve()
        if not temporary_root.is_relative_to(ROOT.resolve()):
            raise RuntimeError("Diretório temporário fora do projeto.")
        temporary_root.mkdir(exist_ok=True)
        self.folder = temporary_root / uuid.uuid4().hex
        self.folder.mkdir()
        self.addCleanup(self.cleanup_folder)

    def cleanup_folder(self):
        if not self.folder.resolve().is_relative_to((ROOT / ".test-tmp").resolve()):
            raise RuntimeError("Recusa de limpeza fora do diretório de teste.")
        shutil.rmtree(self.folder)


class ETLTests(WorkspaceTest):
    def setUp(self):
        super().setUp()
        self.source = self.folder / "raw"
        self.source.mkdir()
        self.output = self.folder / "processed"

    def prepare(self, portuguese, mathematics=None):
        (self.source / "student-por.csv").write_bytes(csv_bytes(portuguese))
        (self.source / "student-mat.csv").write_bytes(csv_bytes(
            mathematics if mathematics is not None else [observation(grade="2")]
        ))

    def read_csv(self, filename):
        with (self.output / filename).open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle, delimiter=";"))

    def test_categories_grade_conversion_zero_and_separate_subject_means(self):
        self.prepare([observation(grade="0"), observation(grade="20"),
                      observation(studytime=" 2 ", grade="13"), observation(studytime="4", grade="10")])
        report = run_etl(self.source, self.output)
        rows = self.read_csv("base_tratada.csv")
        portuguese = [row for row in rows if row["disciplina"] == "Português"]
        self.assertEqual([row["faixa_estudo"] for row in portuguese],
                         ["Menos de 2 horas", "Menos de 2 horas", "2 a 5 horas", "Mais de 10 horas"])
        self.assertEqual([row["nota_final_0_10"] for row in portuguese], ["0", "10", "6,5", "5"])
        self.assertEqual([row["G3"] for row in portuguese], ["0", "20", "13", "10"])
        self.assertNotIn("horas_estudo_semana", rows[0])
        self.assertNotIn("media_horas", report)
        self.assertIsNone(report["total_alunos_unicos"])
        self.assertEqual(report["disciplinas"]["Português"]["media_nota_final_0_20"], 10.75)
        self.assertEqual(report["disciplinas"]["Matemática"]["media_nota_final_0_20"], 2.0)
        summary = self.read_csv("resumo_faixas.csv")
        self.assertEqual((summary[0]["quantidade"], summary[0]["media_nota_final_0_20"], summary[0]["notas_finais_zero"]), ("2", "10,0000", "1"))
        self.assertEqual((summary[2]["quantidade"], summary[2]["media_nota_final_0_20"]), ("0", ""))

    def test_missing_invalid_and_out_of_range_fields_are_not_imputed(self):
        cases = [observation(studytime=value) for value in ("", "0", "5", "1.5", "NaN", "1e0", "aluno@example.com")]
        cases += [observation(grade=value) for value in ("", "21", "-1", "10,5", "Infinity")]
        cases += [observation(G1=""), observation(G2="21")]
        self.prepare(cases)
        report = run_etl(self.source, self.output)
        quality = report["disciplinas"]["Português"]
        self.assertEqual((quality["total_recebidas"], quality["total_validas"], quality["total_excluidas"]), (14, 0, 14))
        self.assertIsNone(quality["media_nota_final_0_20"])
        self.assertFalse(report["pronta_para_analise"])
        for path in self.output.iterdir():
            self.assertNotIn("aluno@example.com", path.read_text(encoding="utf-8-sig"))

    def test_full_duplicates_are_kept_but_equal_analytic_values_are_not_flagged(self):
        original = observation()
        self.prepare([original, observation(context="contexto-b"), original.copy()], mathematics=[original.copy()])
        report = run_etl(self.source, self.output)
        quality = report["disciplinas"]["Português"]
        self.assertEqual((quality["total_validas"], quality["total_excluidas"], quality["registros_para_revisao"]), (3, 0, 1))
        self.assertEqual(report["disciplinas"]["Matemática"]["registros_para_revisao"], 0)
        issue = self.read_csv("ocorrencias.csv")[0]
        self.assertEqual((issue["registro_origem"], issue["registro_relacionado"]), ("3", "1"))
        self.assertEqual(len(self.read_csv("ocorrencias.csv")), 1)

    def test_extra_and_missing_columns_in_records_are_excluded(self):
        self.prepare([observation()])
        path = self.source / "student-por.csv"
        lines = path.read_text(encoding="utf-8").splitlines()
        path.write_text(lines[0] + "\n" + lines[1] + ";EXTRA\n" + lines[1].rsplit(";", 1)[0] + "\n", encoding="utf-8")
        report = run_etl(self.source, self.output)
        self.assertEqual(report["disciplinas"]["Português"]["total_excluidas"], 2)
        self.assertNotIn("EXTRA", (self.output / "ocorrencias.csv").read_text(encoding="utf-8-sig"))

    def test_missing_duplicate_or_personal_headers_fail_before_output(self):
        for fields in (SOURCE_FIELDS[:-1], (*SOURCE_FIELDS, "email"), (*SOURCE_FIELDS[:-1], "G2")):
            with self.subTest(fields=fields):
                self.prepare([])
                (self.source / "student-por.csv").write_bytes(csv_bytes([], fields))
                with self.assertRaisesRegex(ValueError, "Cabeçalho"):
                    run_etl(self.source, self.output)
                self.assertFalse(self.output.exists())

    def test_contextual_attributes_are_not_loaded(self):
        self.prepare([observation(context="nao-exportar-contexto")])
        run_etl(self.source, self.output)
        for path in self.output.iterdir():
            self.assertNotIn("nao-exportar-contexto", path.read_text(encoding="utf-8-sig"))
        headers = self.read_csv("base_tratada.csv")[0]
        self.assertTrue(set(headers).isdisjoint({"age", "sex", "school", "health", "Dalc", "Walc"}))

    def test_raw_integrity_and_rerun_without_accumulation(self):
        self.prepare([observation()])
        before = {path.name: path.read_bytes() for path in self.source.iterdir()}
        report = run_etl(self.source, self.output)
        first = {path.name: path.read_bytes() for path in self.output.glob("*.csv")}
        second = run_etl(self.source, self.output)
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.source.iterdir()})
        self.assertEqual(first, {path.name: path.read_bytes() for path in self.output.glob("*.csv")})
        self.assertEqual(report["disciplinas"], second["disciplinas"])
        saved = json.loads((self.output / "qualidade.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["total_registros_validos"], 2)

    def test_missing_subject_fails_without_partial_output(self):
        (self.source / "student-por.csv").write_bytes(csv_bytes([observation()]))
        with self.assertRaises(FileNotFoundError):
            run_etl(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_output_cannot_be_inside_raw_directory(self):
        self.prepare([observation()])
        for output in (self.source, self.source / "processed"):
            with self.subTest(output=output), self.assertRaises(ValueError):
                run_etl(self.source, output)

    @unittest.skipUnless(all((ROOT / "data/raw/uci" / name).exists() for name in ("student-por.csv", "student-mat.csv")), "Execute a coleta para verificar a integração com a base real.")
    def test_official_dataset_counts_checksums_and_independent_means(self):
        source = ROOT / "data/raw/uci"
        before = {name: (source / name).read_bytes() for name in ("student-por.csv", "student-mat.csv")}
        report = run_etl(source, self.output)
        expected = {
            "Português": (649, [212, 305, 97, 35], 15, "a7594a11d7771c0efe1a740824e0e833da9c4cad07c39a9766a874575563fb3f"),
            "Matemática": (395, [105, 198, 65, 27], 38, "e47f9ee225e1ee6e69b7564e6dac7123e80b8486677fe111f351964cef5dec80"),
        }
        summary = self.read_csv("resumo_faixas.csv")
        for subject, (count, bands, zeros, checksum) in expected.items():
            quality = report["disciplinas"][subject]
            self.assertEqual((quality["total_recebidas"], quality["total_validas"], quality["total_excluidas"], quality["registros_para_revisao"]), (count, count, 0, 0))
            self.assertEqual(quality["notas_finais_zero"], zeros)
            self.assertEqual(quality["entrada_sha256"], checksum)
            with (source / quality["arquivo"]).open(encoding="utf-8", newline="") as handle:
                raw = list(csv.DictReader(handle, delimiter=";"))
            for code, expected_count in enumerate(bands, start=1):
                raw_grades = [int(row["G3"]) for row in raw if int(row["studytime"]) == code]
                result = next(row for row in summary if row["disciplina"] == subject and int(row["studytime"]) == code)
                self.assertEqual(int(result["quantidade"]), expected_count)
                self.assertAlmostEqual(float(result["media_nota_final_0_20"].replace(",", ".")), sum(raw_grades) / len(raw_grades), delta=0.00005)
            self.assertEqual(sum(bands), count)
            self.assertEqual((source / quality["arquivo"]).read_bytes(), before[quality["arquivo"]])


class CollectorTests(WorkspaceTest):
    def package(self, nested=True):
        stream = io.BytesIO()
        with ZipFile(stream, "w") as archive:
            for name in FILES:
                archive.writestr(name, csv_bytes([]) if name.endswith(".csv") else b"Dicionario de teste")
            archive.writestr("../fora.txt", b"nao extrair")
        if not nested:
            return stream.getvalue()
        outer = io.BytesIO()
        with ZipFile(outer, "w") as archive:
            archive.writestr("student.zip", stream.getvalue())
            archive.writestr(".student.zip_old", b"nao usar")
        return outer.getvalue()

    def test_nested_and_direct_packages_only_return_allowed_files(self):
        for nested in (True, False):
            files = read_package(self.package(nested))
            self.assertEqual(set(files), set(FILES))

    def test_local_acquisition_manifest_and_file_integrity(self):
        path = self.folder / "official.zip"
        package = self.package()
        path.write_bytes(package)
        destination = self.folder / "raw"
        metadata = collect(destination, path)
        self.assertEqual(metadata["modo_aquisicao"], "importacao_de_pacote_local")
        self.assertEqual(metadata["pacote_sha256"], hashlib.sha256(package).hexdigest())
        self.assertEqual(set(path.name for path in destination.iterdir()), {*FILES, "manifesto.json"})
        for name, content in read_package(package).items():
            self.assertEqual((destination / name).read_bytes(), content)
        self.assertFalse((self.folder / "fora.txt").exists())

    def test_download_uses_official_https_url(self):
        with patch("scripts.coletar_uci.urlopen", return_value=io.BytesIO(self.package())) as download:
            metadata = collect(self.folder / "raw")
        request = download.call_args.args[0]
        self.assertEqual(request.full_url, DOWNLOAD_URL)
        self.assertEqual(metadata["modo_aquisicao"], "download_oficial_https")

    def test_existing_different_raw_file_is_not_overwritten(self):
        path = self.folder / "official.zip"
        path.write_bytes(self.package())
        destination = self.folder / "raw"
        destination.mkdir()
        (destination / "student-por.csv").write_bytes(b"original diferente")
        with self.assertRaisesRegex(ValueError, "diferente"):
            collect(destination, path)
        self.assertEqual((destination / "student-por.csv").read_bytes(), b"original diferente")
        self.assertFalse((destination / "student-mat.csv").exists())


if __name__ == "__main__":
    unittest.main()
