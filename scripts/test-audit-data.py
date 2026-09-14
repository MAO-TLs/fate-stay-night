from collections import defaultdict
from pathlib import Path
import glob
import json
import unittest

SITE = Path(__file__).resolve().parents[1]
AUDIT = SITE.parent / "audit" / "mirror_moon_v1"


class AuditDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.public_index = json.loads((SITE / "public/data/audit/findings/index.json").read_text())
        cls.script_index = json.loads((SITE / "public/data/script/index.json").read_text())
        cls.dossiers = json.loads((AUDIT / "dossiers.json").read_text())

    def test_every_adjudicated_finding_is_published_or_explicitly_unmapped(self):
        documents = [json.loads((AUDIT / "ledger.json").read_text())]
        documents += [json.loads(Path(path).read_text()) for path in glob.glob(str(AUDIT / "ledger_tranches/*.json"))]
        source_ids = {finding["id"] for document in documents for finding in document["findings"]}
        mapped_ids = set()
        for route in self.public_index["routes"]:
            payload = json.loads((SITE / f'public/data/audit/findings/{route["scriptId"]}.json').read_text())
            self.assertEqual(payload["findingCount"], len(payload["findings"]))
            mapped_ids.update(finding["id"] for finding in payload["findings"])
        unmapped_ids = {finding["id"] for finding in self.public_index["unmapped"]}
        self.assertFalse(mapped_ids & unmapped_ids)
        self.assertEqual(source_ids, mapped_ids | unmapped_ids)
        self.assertEqual(len(source_ids), self.dossiers["corpusConfirmedFindingCount"])
        self.assertEqual(len(mapped_ids), self.public_index["mappedFindings"])
        self.assertEqual(len(unmapped_ids), self.public_index["unmappedFindings"])

    def test_every_mapped_annotation_targets_a_real_public_page(self):
        scripts = {item["id"]: item for item in self.script_index["scripts"]}
        for route in self.public_index["routes"]:
            script_id = route["scriptId"]
            self.assertIn(script_id, scripts)
            pages = json.loads((SITE / f"public/data/script/{script_id}.json").read_text())["pages"]
            refs = {page["ref"] for page in pages}
            payload = json.loads((SITE / f"public/data/audit/findings/{script_id}.json").read_text())
            for finding in payload["findings"]:
                self.assertIn(finding["ref"], refs, finding["id"])
                self.assertTrue(finding["evidenceJa"])
                self.assertTrue(finding["highlight"])
                self.assertTrue(finding["explanation"])

    def test_dossier_links_resolve(self):
        dossier_ids = {
            dossier["id"]
            for group in self.dossiers["groups"]
            for dossier in group["dossiers"]
        }
        self.assertEqual(dossier_ids, set(self.public_index["dossierLabels"]))
        for route in self.public_index["routes"]:
            payload = json.loads((SITE / f'public/data/audit/findings/{route["scriptId"]}.json').read_text())
            for finding in payload["findings"]:
                self.assertLessEqual(set(finding["dossiers"]), dossier_ids)


if __name__ == "__main__":
    unittest.main()
