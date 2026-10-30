"""Check user-visible distinction: one real native sprite, repeated LZ10 loads."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location("stressqa",ROOT/"inject_groudon_vblank_stress_qa.py")
qa=importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)


class VblankQATests(unittest.TestCase):
    def test_append_seven_checks_after_twelve_prior_checks(self):
        source="F.run(function()\n  F.L('GROUDON_CPU samples=1')\n"+qa.END
        changed=qa.inject(source)
        self.assertEqual(changed.count("F.check("),7)
        self.assertIn("GROUDON_STRESS mode=",changed)
        self.assertIn("F.w8(S.gGWStressExtraCopies,mode)",changed)
        self.assertIn("snapshot(\"vblank-stress-",changed)

    def test_refuse_double_injection(self):
        source="F.run(function()\n  F.L('GROUDON_CPU samples=1')\n"+qa.END
        with self.assertRaisesRegex(ValueError,"FAIL CLOSED"):
            qa.inject(qa.inject(source))

    def test_requires_original_timer_and_verified_hashes(self):
        with self.assertRaisesRegex(ValueError,"FAIL CLOSED"):
            qa.inject("F.run(function()\n"+qa.END)
        with self.assertRaisesRegex(ValueError,"FAIL CLOSED"):
            qa.inject("GROUDON_CPU samples=x\n__GROUDON_FNV_LIST__\n"+qa.END)


if __name__=="__main__":
    unittest.main()
