#!/usr/bin/env python3
"""Run actual Python gate acceptance tests and export their results as JUnit."""
import argparse
import sys
import time
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

class JUnitResult(unittest.TextTestResult):
    def startTest(self, test):
        super().startTest(test)
        self.started = time.monotonic()
        self.case = ET.SubElement(self.xml, 'testcase', classname=test.id().rsplit('.', 1)[0],
                                  name=test.id().rsplit('.', 1)[1])

    def stopTest(self, test):
        self.case.set('time', f'{time.monotonic() - self.started:.6f}')
        super().stopTest(test)

    def addFailure(self, test, err):
        super().addFailure(test, err)
        ET.SubElement(self.case, 'failure').text = self._exc_info_to_string(err, test)

    def addError(self, test, err):
        super().addError(test, err)
        ET.SubElement(self.case, 'error').text = self._exc_info_to_string(err, test)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        ET.SubElement(self.case, 'skipped', message=reason)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # Running the file directly must still make eng importable for existing tests.
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    suite = unittest.defaultTestLoader.discover(str(root / 'eng/tests'), top_level_dir=str(root))
    xml = ET.Element('testsuite', name='QualityGateLab gate acceptance')
    def result_factory(*a, **kw):
        result = JUnitResult(*a, **kw)
        result.xml = xml
        return result
    result = unittest.TextTestRunner(verbosity=2, resultclass=result_factory).run(suite)
    xml.set('tests', str(result.testsRun))
    xml.set('failures', str(len(result.failures)))
    xml.set('errors', str(len(result.errors)))
    xml.set('skipped', str(len(result.skipped)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(xml).write(args.output, encoding='utf-8', xml_declaration=True)
    return 0 if result.wasSuccessful() and not result.skipped else 1

if __name__ == '__main__':
    sys.exit(main())
