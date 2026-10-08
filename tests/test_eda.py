import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from scripts.eda import analyze, describe, load_base, percentile, ranks, reconcile, run_eda, spearman
from scripts.etl import BASE_FIELDS

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/uci"


class StatisticsTests(unittest.TestCase):
    def test_quartiles_sample_deviation_and_outliers_keep_zero(self):
        values = [0, 10, 10, 10, 10, 20]
        original = values.copy()
        result = describe(values)
        self.assertEqual((result["media"], result["mediana"], result["q1"], result["q3"]), (10, 10, 10, 10))
        self.assertEqual((result["minimo"], result["maximo"], result["notas_zero"], result["atipicos_iqr"]), (0, 20, 1, 2))
        self.assertAlmostEqual(result["desvio_padrao_amostral"], (200 / 5) ** .5)
        self.assertEqual(values, original)
        self.assertEqual(percentile([0, 10], .25), 2.5)

    def test_empty_singleton_and_constant_values(self):
        self.assertIsNone(describe([])["media"])
        self.assertEqual(describe([])["quantidade"], 0)
        self.assertIsNone(describe([0])["desvio_padrao_amostral"])
        self.assertEqual(describe([0])["notas_zero"], 1)
        self.assertEqual(describe([10, 10])["atipicos_iqr"], 0)
        self.assertIsNone(spearman([1, 1], [0, 20]))
        self.assertIsNone(spearman([], []))

    def test_spearman_tied_ranks_and_both_directions(self):
        self.assertEqual(ranks([3, 1, 1, 2]), [4, 1.5, 1.5, 3])
        self.assertAlmostEqual(spearman([1, 1, 2, 3], [1, 2, 2, 3]), 5 / 6)
        self.assertAlmostEqual(spearman([1, 2, 3], [1, 2, 3]), 1)
        self.assertAlmostEqual(spearman([1, 2, 3], [3, 2, 1]), -1)
        with self.assertRaises(ValueError):
            spearman([1], [1, 2])

    def test_subjects_are_separate_and_empty_bands_are_not_zero_means(self):
        rows = [{"disciplina": subject, "studytime": 1, "G1": grade, "G2": grade,
                 "G3": grade, "sinalizacoes": ""} for subject, grade in (("Português", 0), ("Português", 20), ("Matemática", 2))]
        result = analyze(rows)
        self.assertEqual(result["disciplinas"]["Português"]["notas"]["G3"]["media"], 10)
        self.assertEqual(result["disciplinas"]["Matemática"]["notas"]["G3"]["media"], 2)
        self.assertIsNone(result["disciplinas"]["Português"]["faixas"][1]["media"])
        self.assertEqual(len(result["correlacoes"]), 6)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        temporary_root = ROOT / ".test-tmp"
        temporary_root.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=temporary_root)
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)

    def write_base(self, rows):
        path = self.folder / "base.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=BASE_FIELDS, delimiter=";")
            writer.writeheader()
            writer.writerows(rows)
        return path

    def fixture(self):
        return [{"disciplina": subject, "registro_origem": 1, "studytime": 1,
                 "faixa_estudo": "Menos de 2 horas", "G1": 10, "G2": 10, "G3": 10,
                 "nota_final_0_10": "5", "sinalizacoes": ""} for subject in ("Português", "Matemática")]

    def test_validation_without_deduplicating_equal_grades(self):
        rows = self.fixture()
        rows.append(rows[0] | {"registro_origem": 2})
        self.assertEqual(len(load_base(self.write_base(rows))), 3)
        for changes in ({"G3": ""}, {"G3": "21"}, {"nota_final_0_10": "6"},
                        {"faixa_estudo": "horas exatas"}, {"registro_origem": "0"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                load_base(self.write_base([rows[0] | changes, rows[1]]))
        with self.assertRaises(ValueError):
            load_base(self.write_base([rows[0], rows[0], rows[1]]))

    def test_stale_quality_fails_before_creating_output(self):
        for name in ("base_tratada.csv", "qualidade.json", "resumo_faixas.csv"):
            (self.folder / name).write_bytes((SOURCE / name).read_bytes())
        path = self.folder / "qualidade.json"
        quality = json.loads(path.read_text(encoding="utf-8"))
        quality["total_registros_validos"] += 1
        path.write_text(json.dumps(quality), encoding="utf-8")
        output = self.folder.parent / (self.folder.name + "-output")
        with self.assertRaisesRegex(ValueError, "Contagem"):
            run_eda(self.folder, output)
        self.assertFalse(output.exists())

    def test_input_and_raw_directories_are_protected(self):
        for output in (SOURCE, SOURCE / "eda", ROOT / "data/raw/eda"):
            with self.subTest(output=output), self.assertRaisesRegex(ValueError, "fora"):
                run_eda(SOURCE, output)

    def test_real_data_reconciles_and_matches_published_counts(self):
        rows = load_base(SOURCE / "base_tratada.csv")
        quality = json.loads((SOURCE / "qualidade.json").read_text(encoding="utf-8"))
        reconcile(rows, quality, SOURCE / "resumo_faixas.csv")
        result = analyze(rows)
        expected = {"Português": (649, [212, 305, 97, 35], 15, 11.906009244992296),
                    "Matemática": (395, [105, 198, 65, 27], 38, 10.415189873417722)}
        for subject, (count, bands, zeros, mean) in expected.items():
            data = result["disciplinas"][subject]
            self.assertEqual(data["notas"]["G3"]["quantidade"], count)
            self.assertEqual([band["quantidade"] for band in data["faixas"]], bands)
            self.assertEqual(data["notas"]["G3"]["notas_zero"], zeros)
            self.assertAlmostEqual(data["notas"]["G3"]["media"], mean)
            self.assertLess(data["faixas"][3]["media"], data["faixas"][2]["media"])

    @unittest.skipUnless(importlib.util.find_spec("matplotlib"), "Instale requirements-eda.txt para verificar os gráficos.")
    def test_complete_outputs_preserve_input_and_link_to_existing_charts(self):
        before = {path.name: path.read_bytes() for path in SOURCE.iterdir() if path.is_file()}
        output = self.folder / "report"
        result = run_eda(SOURCE, output)
        self.assertEqual(len(list((output / "graficos").glob("*.svg"))), 8)
        self.assertEqual(len(list((output / "graficos").glob("*.png"))), 8)
        self.assertEqual(before, {path.name: path.read_bytes() for path in SOURCE.iterdir() if path.is_file()})
        saved = json.loads((output / "indicadores.json").read_text(encoding="utf-8"))
        self.assertEqual(saved, result)
        html = (output / "relatorio.html").read_text(encoding="utf-8")
        for path in (output / "graficos").glob("*.svg"):
            self.assertIn(f'src="graficos/{path.name}"', html)
        markdown = (output / "relatorio.md").read_text(encoding="utf-8")
        self.assertNotIn("|\n\n|", markdown)
        self.assertIn("sem interpretação causal", markdown)


if __name__ == "__main__":
    unittest.main()
