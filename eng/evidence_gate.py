#!/usr/bin/env python3
"""Build and verify a release evidence bundle from actual CI test reports."""
import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path

try:
    from eng.coverage_gate import aggregate_line_coverage, coverage_percentage, resolve_reports
except ModuleNotFoundError:
    from coverage_gate import aggregate_line_coverage, coverage_percentage, resolve_reports

CATEGORIES = {'unit', 'integration', 'coverage', 'uat'}

def require(condition, message):
    if not condition:
        raise ValueError(message)

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')

def test_results(path):
    """Read TRX or JUnit and fail closed on empty, skipped or failing suites."""
    root = ET.parse(path).getroot()
    tag = root.tag.split('}')[-1]
    if tag == 'TestRun':
        results = root.findall('.//{*}UnitTestResult')
        require(results, f'No test results: {path.name}')
        states = [(r.get('testName', ''), r.get('outcome') == 'Passed') for r in results]
        counters = root.find('.//{*}Counters')
        require(counters is not None, f'Missing TRX counters: {path.name}')
        require(int(counters.get('total', '-1')) == len(results) and
                int(counters.get('passed', '-1')) == len(results), f'Incomplete TRX results: {path.name}')
        summary = root.find('.//{*}ResultSummary')
        require(summary is not None and summary.get('outcome') in ('Completed', 'Passed'),
                f'Unsuccessful TRX summary: {path.name}')
    elif tag in ('testsuite', 'testsuites'):
        results = root.findall('.//testcase')
        require(results, f'No test cases: {path.name}')
        states = [(r.get('classname', '') + '.' + r.get('name', ''),
                   not any(r.find(t) is not None for t in ('failure', 'error', 'skipped'))) for r in results]
        suites = [root] if tag == 'testsuite' else root.findall('.//testsuite')
        require(suites, f'No test suites: {path.name}')
        for suite in suites:
            require(int(suite.get('tests', '-1')) == len(suite.findall('./testcase')),
                    f'Incomplete JUnit results: {path.name}')
            require(all(int(suite.get(t, '0')) == 0 for t in ('failures', 'errors', 'skipped')),
                    f'Unsuccessful JUnit suite: {path.name}')
    else:
        raise ValueError(f'Unsupported test report: {path.name}')
    require(all(name and passed for name, passed in states), f'Failed or skipped tests: {path.name}')
    return {name for name, _ in states}

def validate_record(record, as_of):
    require(record['scope'] == 'portfolio-demonstration', 'Unsupported change-record scope')
    for field in ('change_id', 'summary', 'owner', 'reviewer', 'reviewed_at', 'rollback', 'risk'):
        require(record.get(field), f'Missing change field: {field}')
    require(record['review_status'] == 'accepted', 'Missing accepted review decision')
    require(date.fromisoformat(record['reviewed_at']) <= as_of, 'Review date is in the future')
    cases = record['acceptance_cases']
    require(cases, 'Missing acceptance cases')
    require(len({c['id'] for c in cases}) == len(cases), 'Duplicate acceptance-case IDs')
    for case in cases:
        require(case.get('id') and case.get('requirement') and case.get('test'), 'Incomplete acceptance case')
    findings = record['security_findings']
    require(len({f['id'] for f in findings}) == len(findings), 'Duplicate finding IDs')
    for finding in findings:
        for field in ('id', 'severity', 'owner', 'description', 'due_date', 'status'):
            require(finding.get(field), f'Missing finding field: {field}')
        require(finding['severity'] in ('critical', 'high', 'medium', 'low'), 'Invalid finding severity')
        require(finding['status'] in ('open', 'closed', 'exception'), 'Invalid finding status')
        deadline = date.fromisoformat(finding['due_date'])
        if finding['status'] == 'closed':
            require(finding.get('verification'), 'Closed finding requires verification')
        if finding['status'] == 'open':
            require(finding['severity'] not in ('critical', 'high'), f"Unresolved security finding: {finding['id']}")
            require(deadline >= as_of, f"Overdue security finding: {finding['id']}")
        if finding['status'] == 'exception':
            exception = finding['exception']
            require(exception.get('reviewer') and exception.get('reason'), 'Incomplete exception decision')
            require(exception['reviewer'] != finding['owner'], 'Exception requires a separate reviewer')
            require(date.fromisoformat(exception['expires']) > as_of, f"Expired exception: {finding['id']}")

def assess(bundle, manifest, as_of, expected_source):
    require(re.fullmatch(r'[0-9a-f]{40}', manifest['source_revision']), 'Invalid source revision')
    require(manifest['source_revision'] == expected_source, 'Evidence belongs to another source revision')
    require(manifest['run_id'], 'Missing pipeline run identity')
    require(0 <= manifest['coverage_threshold'] <= 100, 'Invalid coverage threshold')
    entries = manifest['artifacts']
    paths = [e['path'] for e in entries]
    require(len(paths) == len(set(paths)), 'Duplicate artifact paths')
    require({e['category'] for e in entries} == CATEGORIES, 'Missing required evidence category')
    require(manifest['record']['path'] == 'change-record.json', 'Invalid change-record path')
    all_entries = entries + [manifest['record']]
    for entry in all_entries:
        relative = Path(entry['path'])
        require(not relative.is_absolute() and '..' not in relative.parts and
                '\\' not in entry['path'], 'Unsafe evidence path')
        path = bundle / relative
        require(path.resolve().is_relative_to(bundle.resolve()), 'Evidence path escapes bundle')
        require(path.is_file() and not path.is_symlink(), f'Missing evidence file: {relative}')
        require(sha256(path) == entry['sha256'], f'Evidence hash mismatch: {relative}')
    record = read_json(bundle / 'change-record.json')
    require(manifest['change_id'] == record['change_id'], 'Change identity mismatch')
    validate_record(record, as_of)
    names = set()
    counts = {}
    for category in ('unit', 'integration', 'uat'):
        category_names = set()
        for entry in entries:
            if entry['category'] == category:
                category_names |= test_results(bundle / entry['path'])
        counts[category] = len(category_names)
        names |= category_names
    for case in record['acceptance_cases']:
        require(case['test'] in names, f"Missing passing acceptance test: {case['id']}")
    coverage_paths = [bundle / e['path'] for e in entries if e['category'] == 'coverage']
    covered, total = aggregate_line_coverage(coverage_paths, include_packages=['QualityGateLab.Api'])
    coverage = coverage_percentage(covered, total)
    require(coverage >= manifest['coverage_threshold'], 'Coverage below evidence threshold')
    return {'change_id': record['change_id'], 'source_revision': expected_source,
            'test_counts': counts, 'coverage_percentage': round(coverage, 2),
            'acceptance_cases': [{'id': c['id'], 'requirement': c['requirement'],
                                  'test': c['test'], 'result': 'passed'} for c in record['acceptance_cases']]}

def build(record_path, reports, output, source, run_id, as_of, threshold=70):
    require(not output.exists(), 'Evidence directory already exists; use a fresh directory')
    output.mkdir(parents=True)
    shutil.copyfile(record_path, output / 'change-record.json')
    manifest = {'schema_version': 1, 'source_revision': source, 'run_id': run_id,
                'generated_at': datetime.now(timezone.utc).isoformat(), 'as_of': str(as_of),
                'coverage_threshold': threshold, 'change_id': read_json(record_path).get('change_id'),
                'record': {'path': 'change-record.json', 'sha256': sha256(output / 'change-record.json')},
                'artifacts': []}
    for category, patterns in reports.items():
        require(category in CATEGORIES, 'Unsupported evidence category')
        for index, original in enumerate(resolve_reports(patterns)):
            target = output / category / f'{index:03d}-{original.name}'
            target.parent.mkdir(exist_ok=True)
            shutil.copyfile(original, target)
            manifest['artifacts'].append({'category': category, 'path': target.relative_to(output).as_posix(),
                                          'sha256': sha256(target)})
    write_json(output / 'manifest.json', manifest)
    return verify(output, source, as_of)

def verify(output, source, as_of=None):
    manifest = read_json(output / 'manifest.json')
    try:
        require(manifest['schema_version'] == 1, 'Unsupported manifest schema')
        result = assess(output, manifest, as_of or date.fromisoformat(manifest['as_of']), source)
    except (ValueError, KeyError, TypeError, OSError, ET.ParseError) as error:
        write_json(output / 'gate-result.json', {'status': 'failed', 'reason': str(error)})
        raise
    result['status'] = 'passed'
    write_json(output / 'gate-result.json', result)
    with (output / 'uat-results.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=['id', 'requirement', 'test', 'result'])
        writer.writeheader()
        writer.writerows(result['acceptance_cases'])
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    create = sub.add_parser('build')
    create.add_argument('--record', type=Path, required=True)
    for name in ('unit', 'integration', 'coverage', 'uat'):
        create.add_argument(f'--{name}-reports', nargs='+', required=True)
    create.add_argument('--run-id', required=True)
    create.add_argument('--threshold', type=float, default=70)
    create.add_argument('--as-of', type=date.fromisoformat, default=date.today())
    check = sub.add_parser('verify')
    check.add_argument('--as-of', type=date.fromisoformat)
    for command in (create, check):
        command.add_argument('--output', type=Path, required=True)
        command.add_argument('--source-revision', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'build':
            reports = {name: getattr(args, name + '_reports') for name in CATEGORIES}
            result = build(args.record, reports, args.output, args.source_revision,
                           args.run_id, args.as_of, args.threshold)
        else:
            result = verify(args.output, args.source_revision, args.as_of)
        print(f"PASS: release evidence for {result['change_id']}; coverage {result['coverage_percentage']}%")
        return 0
    except (ValueError, KeyError, TypeError, OSError, ET.ParseError) as error:
        print(f'FAIL: {error}')
        return 1

if __name__ == '__main__':
    sys.exit(main())
