import unittest
from src.common import normalize_skills, salary_rur


class CommonTests(unittest.TestCase):
    def test_skills_are_deduplicated_and_sorted(self):
        self.assertEqual(normalize_skills("Docker; Linux; docker;  Git "), ["Docker", "Git", "Linux"])

    def test_salary_midpoint_and_net_to_gross(self):
        self.assertEqual(salary_rur({"currency":"RUR","salary_from":"100","salary_to":"200","gross":"true"}),150)
        self.assertAlmostEqual(salary_rur({"currency":"RUR","salary_from":"87","salary_to":"","gross":"false"}),100)


if __name__ == "__main__": unittest.main()

