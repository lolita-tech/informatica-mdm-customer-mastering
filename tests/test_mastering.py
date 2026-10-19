import json
import unittest
from pathlib import Path
from src.mastering import build
class MasteringTests(unittest.TestCase):
    def setUp(self): self.rows=json.loads(Path("data/sample.json").read_text())["customers"]
    def test_golden_and_crosswalk(self):
        r=build(self.rows,[])
        self.assertEqual(len(r["dim_customer"]),2)
        self.assertEqual(len(r["customer_crosswalk"]),3)
    def test_shared_email_held(self):
        self.assertEqual(sum(r["reason"]=="EMAIL_ID_CONFLICT" for r in build(self.rows,[])["exceptions"]),2)
    def test_crm_survives(self):
        self.assertIn("Avery Example",[r["name"] for r in build(self.rows,[])["dim_customer"]])
    def test_stable_identity(self):
        self.assertEqual(build(self.rows,[]),build(list(reversed(self.rows)),[]))
    def test_missing_identity_held(self):
        self.assertEqual(sum(r["reason"]=="MISSING_TRUSTED_ID" for r in build(self.rows,[])["exceptions"]),1)
