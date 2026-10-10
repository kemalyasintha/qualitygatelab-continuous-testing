import copy
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from eng import evidence_gate as gate

TRX = '''<TestRun xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010">
<Results><UnitTestResult testName="ApiTests.CreateOrder" outcome="Passed" /></Results>
<ResultSummary outcome="Completed"><Counters total="1" passed="1" /></ResultSummary></TestRun>'''
JUNIT = '''<testsuite tests="1" failures="0" errors="0" skipped="0">
<testcase classname="GateTests" name="valid_evidence" /></testsuite>'''
COVERAGE = '''<coverage><packages><package name="QualityGateLab.Api"><classes>
<class filename="src/Orders.cs"><lines><line number="1" hits="1" /></lines></class>
</classes></package></packages></coverage>'''

class EvidenceGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / 'bundle'
        self.source = 'a' * 40
        self.as_of = date(2026, 10, 10)
        self.record = {'scope': 'portfolio-demonstration', 'change_id': 'TEST-001',
                       'summary': 'Test fixture', 'owner': 'demo-owner', 'reviewer': 'demo-reviewer',
                       'review_status': 'accepted', 'reviewed_at': '2026-10-10',
                       'rollback': 'Revert reviewed test change', 'risk': 'Fixture only',
                       'acceptance_cases': [{'id': 'TEST-UAT', 'requirement': 'Passing evidence',
                                             'test': 'GateTests.valid_evidence'}], 'security_findings': []}
        self.record_path = self.root / 'change.json'
        self.reports = {}
        for category, content, suffix in [('unit', TRX, 'trx'), ('integration', TRX, 'trx'),
                                          ('coverage', COVERAGE, 'xml'), ('uat', JUNIT, 'xml')]:
            path = self.root / f'{category}.{suffix}'
            path.write_text(content)
            self.reports[category] = [str(path)]

    def build(self):
        gate.write_json(self.record_path, self.record)
        return gate.build(self.record_path, self.reports, self.output, self.source, 'test-run', self.as_of)

    def finding(self, status='open', severity='high'):
        return {'id': 'TEST-FIND-001', 'severity': severity, 'owner': 'demo-owner',
                'description': 'Synthetic finding', 'status': status, 'due_date': '2026-10-20'}

    def test_complete_bundle_passes(self):
        result = self.build()
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['coverage_percentage'], 100)
        self.assertEqual(result['test_counts'], {'unit': 1, 'integration': 1, 'uat': 1})
        self.assertTrue((self.output / 'uat-results.csv').is_file())
        self.assertEqual(gate.verify(self.output, self.source)['status'], 'passed')

    def test_missing_category_fails(self):
        self.reports['integration'] = [str(self.root / 'missing.trx')]
        with self.assertRaisesRegex(ValueError, 'required evidence category'):
            self.build()
        self.assertEqual(gate.read_json(self.output / 'gate-result.json')['status'], 'failed')

    def test_missing_acceptance_test_fails(self):
        self.record['acceptance_cases'][0]['test'] = 'Missing.test'
        with self.assertRaisesRegex(ValueError, 'passing acceptance test'):
            self.build()

    def test_failed_test_fails(self):
        Path(self.reports['unit'][0]).write_text(TRX.replace('outcome="Passed"', 'outcome="Failed"'))
        with self.assertRaisesRegex(ValueError, 'Failed or skipped'):
            self.build()

    def test_incomplete_trx_counters_fail(self):
        Path(self.reports['unit'][0]).write_text(TRX.replace('total="1"', 'total="2"'))
        with self.assertRaisesRegex(ValueError, 'Incomplete TRX'):
            self.build()

    def test_empty_report_fails(self):
        Path(self.reports['unit'][0]).write_text('<TestRun/>')
        with self.assertRaisesRegex(ValueError, 'No test results'):
            self.build()

    def test_skipped_uat_fails(self):
        Path(self.reports['uat'][0]).write_text(JUNIT.replace(' />', '><skipped/></testcase>'))
        with self.assertRaisesRegex(ValueError, 'Failed or skipped'):
            self.build()

    def test_missing_review_decision_fails(self):
        self.record['review_status'] = 'pending'
        with self.assertRaisesRegex(ValueError, 'accepted review'):
            self.build()

    def test_open_high_finding_fails(self):
        self.record['security_findings'] = [self.finding()]
        with self.assertRaisesRegex(ValueError, 'Unresolved security finding'):
            self.build()

    def test_overdue_medium_finding_fails(self):
        finding = self.finding(severity='medium')
        finding['due_date'] = '2026-10-09'
        self.record['security_findings'] = [finding]
        with self.assertRaisesRegex(ValueError, 'Overdue security finding'):
            self.build()

    def test_exception_valid_until_future_date_passes(self):
        finding = self.finding(status='exception')
        finding['exception'] = {'reviewer': 'risk-reviewer', 'reason': 'Synthetic acceptance', 'expires': '2026-10-11'}
        self.record['security_findings'] = [finding]
        self.assertEqual(self.build()['status'], 'passed')

    def test_expired_exception_fails(self):
        finding = self.finding(status='exception')
        finding['exception'] = {'reviewer': 'risk-reviewer', 'reason': 'Synthetic acceptance', 'expires': '2026-10-10'}
        self.record['security_findings'] = [finding]
        with self.assertRaisesRegex(ValueError, 'Expired exception'):
            self.build()

    def test_self_reviewed_exception_fails(self):
        finding = self.finding(status='exception')
        finding['exception'] = {'reviewer': finding['owner'], 'reason': 'Synthetic', 'expires': '2026-10-11'}
        self.record['security_findings'] = [finding]
        with self.assertRaisesRegex(ValueError, 'separate reviewer'):
            self.build()

    def test_closed_finding_needs_verification(self):
        self.record['security_findings'] = [self.finding(status='closed')]
        with self.assertRaisesRegex(ValueError, 'requires verification'):
            self.build()

    def test_tampered_evidence_fails(self):
        self.build()
        (self.output / 'unit/000-unit.trx').write_text(TRX + '\n')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            gate.verify(self.output, self.source)

    def test_deleted_evidence_fails(self):
        self.build()
        (self.output / 'unit/000-unit.trx').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing evidence file'):
            gate.verify(self.output, self.source)

    def test_other_source_revision_fails(self):
        self.build()
        with self.assertRaisesRegex(ValueError, 'another source revision'):
            gate.verify(self.output, 'b' * 40)

    def test_path_traversal_fails(self):
        self.build()
        path = self.output / 'manifest.json'
        manifest = gate.read_json(path)
        manifest['artifacts'][0]['path'] = '../outside'
        gate.write_json(path, manifest)
        with self.assertRaisesRegex(ValueError, 'Unsafe evidence path'):
            gate.verify(self.output, self.source)

    def test_low_coverage_fails(self):
        Path(self.reports['coverage'][0]).write_text(COVERAGE.replace('hits="1"', 'hits="0"'))
        with self.assertRaisesRegex(ValueError, 'below evidence threshold'):
            self.build()

    def test_existing_bundle_is_not_overwritten(self):
        self.build()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.build()

if __name__ == '__main__':
    unittest.main()
