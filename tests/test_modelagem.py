import copy
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from scripts.eda import load_base
from scripts.modelagem import SCENARIOS, features, fit_scenario, metrics, mine_training, run_modeling, split_data

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/uci"
AVAILABLE = all(importlib.util.find_spec(name) for name in ("sklearn", "numpy", "matplotlib", "joblib"))


@unittest.skipUnless(AVAILABLE, "Instale requirements-modelagem.txt para verificar a modelagem.")
class ModelingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load_base(SOURCE / "base_tratada.csv")
        cls.portuguese = [row for row in cls.rows if row["disciplina"] == "Português"]

    def test_metrics_in_grade_points_keep_negative_r2_and_out_of_range_predictions(self):
        result = metrics([0, 10, 20], [2, 8, 23])
        self.assertAlmostEqual(result["mae"], 7 / 3)
        self.assertAlmostEqual(result["rmse"], (17 / 3) ** .5)
        self.assertAlmostEqual(result["vies"], 1)
        self.assertEqual(result["fora_escala"], 1)
        self.assertLess(metrics([1, 2], [20, 20])["r2"], 0)
        self.assertIsNone(metrics([0, 0], [2, 2])["r2"])
        self.assertIsNone(metrics([0], [2])["r2"])

    def test_holdout_and_folds_are_disjoint_complete_reproducible_and_stratified(self):
        import numpy as np
        for subject in ("Português", "Matemática"):
            rows = [row for row in self.rows if row["disciplina"] == subject]
            train, test, folds = split_data(rows)
            train2, test2, _ = split_data(rows)
            np.testing.assert_array_equal(train, train2)
            np.testing.assert_array_equal(test, test2)
            self.assertFalse(set(train) & set(test))
            self.assertEqual(set(train) | set(test), set(range(len(rows))))
            validation = []
            for fitting, validating in folds:
                self.assertFalse(set(fitting) & set(validating))
                self.assertFalse(set(train[validating]) & set(test))
                self.assertEqual({rows[int(i)]["studytime"] for i in train[validating]}, {1, 2, 3, 4})
                validation.extend(validating)
            self.assertEqual(sorted(validation), list(range(len(train))))
            self.assertEqual(sum(rows[int(i)]["G3"] == 0 for i in list(train) + list(test)),
                             sum(row["G3"] == 0 for row in rows))

    def test_features_reject_target_conversion_and_identifiers(self):
        for forbidden in (("G3",), ("nota_final_0_10",), ("registro_origem",), ("studytime", "G3")):
            with self.subTest(forbidden=forbidden), self.assertRaises(ValueError):
                features(self.portuguese, forbidden)
        x = features(self.portuguese, ("studytime",))
        self.assertEqual(x.shape, (649, 1))

    def test_test_data_does_not_influence_selection_or_fitted_preprocessing(self):
        import numpy as np
        train, test, folds = split_data(self.portuguese)
        fields = SCENARIOS["estudo_e_notas"][1]
        result, fitted = fit_scenario(self.portuguese, fields, train, test, folds)
        changed = copy.deepcopy(self.portuguese)
        for i in test:
            changed[int(i)].update(G1=20, G2=20, G3=20)
        other, other_fitted = fit_scenario(changed, fields, train, test, folds)
        self.assertEqual(result["selecionado"], other["selecionado"])
        self.assertEqual(result["busca_cv"], other["busca_cv"])
        self.assertNotEqual(result["modelos"][0]["teste_mae"], other["modelos"][0]["teste_mae"])
        scaler = fitted.named_steps["preparo"].named_transformers_["notas"]
        np.testing.assert_allclose(scaler.mean_, np.mean([[self.portuguese[int(i)][key] for key in ("G1", "G2")] for i in train], axis=0))
        np.testing.assert_array_equal(scaler.mean_, other_fitted.named_steps["preparo"].named_transformers_["notas"].mean_)
        transform = fitted.named_steps["preparo"].transform(features(self.portuguese[:4], fields))
        self.assertEqual(transform.shape[1], 6)  # Quatro indicadores de faixa + duas notas.
        np.testing.assert_array_equal(transform[:, :4].sum(axis=1), [1, 1, 1, 1])

    def test_mining_support_and_eta_squared_on_known_data(self):
        rows = [{"studytime": band, "G3": 0 if band < 3 else 20} for band in range(1, 5)]
        mined = mine_training(rows)
        self.assertEqual(mined["eta_quadrado"], 1)
        self.assertEqual(sum(item["suporte"] for item in mined["faixas"]), 1)
        self.assertEqual([item["diferenca_media_geral"] for item in mined["faixas"]], [-10, -10, 10, 10])
        self.assertIsNone(mine_training([row | {"G3": 0} for row in rows])["eta_quadrado"])

    def test_too_few_records_fail_with_explicit_message(self):
        with self.assertRaisesRegex(ValueError, "dez registros"):
            split_data(self.portuguese[:4])


@unittest.skipUnless(AVAILABLE, "Instale requirements-modelagem.txt para verificar a modelagem.")
class PipelineTests(unittest.TestCase):
    def setUp(self):
        temporary_root = ROOT / ".test-tmp"
        temporary_root.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=temporary_root)
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)

    def test_protected_directories_cannot_be_used_as_output(self):
        for output in (SOURCE, SOURCE.parent, SOURCE / "modelagem", ROOT, ROOT / "data/raw/modelagem", ROOT / "reports/eda", ROOT / "scripts"):
            with self.subTest(output=output), self.assertRaisesRegex(ValueError, "fora"):
                run_modeling(SOURCE, output)

    def test_stale_or_unapproved_quality_fails_before_output(self):
        source = self.folder / "source"
        source.mkdir()
        for name in ("base_tratada.csv", "qualidade.json", "resumo_faixas.csv"):
            (source / name).write_bytes((SOURCE / name).read_bytes())
        path = source / "qualidade.json"
        quality = json.loads(path.read_text(encoding="utf-8"))
        for changes, message in (({"total_registros_validos": 0}, "Contagem"), ({"pronta_para_analise": False}, "pendências")):
            path.write_text(json.dumps(quality | changes), encoding="utf-8")
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, message):
                run_modeling(source, self.folder / "report")
            self.assertFalse((self.folder / "report").exists())

    def test_complete_pipeline_preserves_inputs_and_exports_reusable_train_only_models(self):
        import joblib
        import numpy as np
        before = {path.name: path.read_bytes() for path in SOURCE.iterdir() if path.is_file()}
        output = self.folder / "report"
        result = run_modeling(SOURCE, output)
        self.assertEqual(before, {path.name: path.read_bytes() for path in SOURCE.iterdir() if path.is_file()})
        self.assertEqual(result, json.loads((output / "resultados.json").read_text(encoding="utf-8")))
        self.assertEqual(result["entradas_sha256"]["base_tratada.csv"], hashlib.sha256(before["base_tratada.csv"]).hexdigest())
        with (output / "metricas.csv").open(encoding="utf-8-sig", newline="") as handle:
            self.assertEqual(len(list(csv.DictReader(handle, delimiter=";"))), 18)
        self.assertEqual(len(list((output / "modelos").glob("*.joblib"))), 6)
        for suffix in ("svg", "png"):
            self.assertEqual(len(list((output / "graficos").glob("*." + suffix))), 2)
        rows = load_base(SOURCE / "base_tratada.csv")
        for subject, slug, train_count, test_count in (("Português", "portugues", 519, 130), ("Matemática", "matematica", 316, 79)):
            group = [row for row in rows if row["disciplina"] == subject]
            train, test, _ = split_data(group)
            data = result["disciplinas"][subject]
            self.assertEqual((data["particao"]["treino"], data["particao"]["teste"]), (train_count, test_count))
            self.assertEqual(data["mineracao_treino"]["quantidade"], train_count)
            for scenario, (_, fields) in SCENARIOS.items():
                item = data["cenarios"][scenario]
                best = next(m for m in item["modelos"] if m["selecionado_cv"])
                self.assertEqual(best["cv_mae"], min(m["cv_mae"] for m in item["modelos"]))
                self.assertEqual(len(item["busca_cv"]), 11)
                self.assertEqual(sum(b["quantidade"] for b in item["teste_por_faixa"]), test_count)
                fitted = joblib.load(output / "modelos" / f"{slug}_{scenario}.joblib")
                prediction = fitted.predict(features(group, fields)[test])
                measured = metrics(np.array([row["G3"] for row in group])[test], prediction)
                self.assertAlmostEqual(measured["mae"], best["teste_mae"])
                # A constante mediana é estimada somente em treino.
                reference = next(m for m in item["modelos"] if m["modelo"] == "mediana")
                baseline_prediction = np.full(len(test), np.median([group[int(i)]["G3"] for i in train]))
                self.assertAlmostEqual(metrics([group[int(i)]["G3"] for i in test], baseline_prediction)["mae"], reference["teste_mae"])
        markdown = (output / "relatorio.md").read_text(encoding="utf-8")
        self.assertNotIn("|\n\n|", markdown)
        self.assertIn("não demonstram causalidade", markdown)
        self.assertNotIn("registro_origem", (output / "resultados.json").read_text(encoding="utf-8"))
        html = (output / "relatorio.html").read_text(encoding="utf-8")
        for path in (output / "graficos").glob("*.svg"):
            self.assertIn(f"graficos/{path.name}", html)


if __name__ == "__main__":
    unittest.main()
