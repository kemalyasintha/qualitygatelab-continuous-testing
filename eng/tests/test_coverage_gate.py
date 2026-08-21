from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from eng.coverage_gate import (
    aggregate_line_coverage,
    coverage_percentage,
    resolve_reports,
)


REPORT_ONE = """\
<?xml version="1.0" encoding="utf-8"?>
<coverage>
  <packages>
    <package name="QualityGateLab.Api">
      <classes>
        <class name="Order" filename="src/Order.cs">
          <lines>
            <line number="10" hits="1" />
            <line number="11" hits="0" />
          </lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
"""

REPORT_TWO = """\
<?xml version="1.0" encoding="utf-8"?>
<coverage>
  <packages>
    <package name="QualityGateLab.Api">
      <classes>
        <class name="Order" filename="src\\Order.cs">
          <lines>
            <line number="11" hits="2" />
            <line number="12" hits="0" />
          </lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
"""


class CoverageGateTests(unittest.TestCase):
    def test_aggregate_uses_union_of_source_lines_and_highest_hit_count(self) -> None:
        with TemporaryDirectory() as directory:
            first = Path(directory) / "unit" / "coverage.cobertura.xml"
            second = Path(directory) / "integration" / "coverage.cobertura.xml"
            first.parent.mkdir()
            second.parent.mkdir()
            first.write_text(REPORT_ONE, encoding="utf-8")
            second.write_text(REPORT_TWO, encoding="utf-8")

            covered, total = aggregate_line_coverage([first, second])

            self.assertEqual(2, covered)
            self.assertEqual(3, total)
            self.assertAlmostEqual(66.67, coverage_percentage(covered, total), places=2)

    def test_resolve_reports_supports_recursive_globs(self) -> None:
        with TemporaryDirectory() as directory:
            report = Path(directory) / "nested" / "coverage.cobertura.xml"
            report.parent.mkdir()
            report.write_text(REPORT_ONE, encoding="utf-8")

            reports = resolve_reports([f"{directory}/**/coverage.cobertura.xml"])

            self.assertEqual([report.resolve()], reports)

    def test_empty_coverage_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "executable lines"):
            coverage_percentage(0, 0)

    def test_aggregate_can_limit_coverage_to_application_sources(self) -> None:
        with TemporaryDirectory() as directory:
            report = Path(directory) / "coverage.cobertura.xml"
            report.write_text(
                REPORT_ONE.replace(
                    "</classes>",
                    """
        <class name="OrderTests" filename="tests/OrderTests.cs">
          <lines><line number="1" hits="1" /></lines>
        </class>
      </classes>""",
                ),
                encoding="utf-8",
            )

            covered, total = aggregate_line_coverage([report], ["src/"])

            self.assertEqual(1, covered)
            self.assertEqual(2, total)

    def test_aggregate_can_select_the_application_package(self) -> None:
        test_package = REPORT_ONE.replace(
            'package name="QualityGateLab.Api"',
            'package name="QualityGateLab.UnitTests"',
        ).replace('filename="src/Order.cs"', 'filename="Orders/OrderTests.cs"')

        with TemporaryDirectory() as directory:
            application_report = Path(directory) / "application.cobertura.xml"
            test_report = Path(directory) / "tests.cobertura.xml"
            application_report.write_text(REPORT_ONE, encoding="utf-8")
            test_report.write_text(test_package, encoding="utf-8")

            covered, total = aggregate_line_coverage(
                [application_report, test_report],
                include_packages=["QualityGateLab.Api"],
            )

            self.assertEqual(1, covered)
            self.assertEqual(2, total)


if __name__ == "__main__":
    unittest.main()
