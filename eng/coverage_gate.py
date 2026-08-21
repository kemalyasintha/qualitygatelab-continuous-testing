#!/usr/bin/env python3
"""Fail CI when aggregate Cobertura line coverage is below a threshold."""

from __future__ import annotations

import argparse
import glob
import sys
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from pathlib import Path


def resolve_reports(patterns: Iterable[str]) -> list[Path]:
    """Resolve file paths and recursive glob patterns without duplicates."""

    resolved: set[Path] = set()

    for pattern in patterns:
        matches = glob.glob(pattern, recursive=True)

        if not matches and Path(pattern).is_file():
            matches = [pattern]

        resolved.update(Path(match).resolve() for match in matches if Path(match).is_file())

    return sorted(resolved)


def aggregate_line_coverage(
    report_paths: Iterable[Path], include_prefixes: Iterable[str] = ()
) -> tuple[int, int]:
    """Combine reports by source file and line, counting a line covered if any test hit it."""

    line_hits: dict[tuple[str, int], int] = {}
    normalized_prefixes = tuple(
        prefix.replace("\\", "/").strip("/") for prefix in include_prefixes
    )

    for report_path in report_paths:
        root = ET.parse(report_path).getroot()

        for class_element in root.findall(".//class"):
            filename = class_element.get("filename")
            if not filename:
                continue

            normalized_filename = filename.replace("\\", "/")
            comparable_filename = normalized_filename.strip("/")

            if normalized_prefixes and not any(
                comparable_filename.startswith(prefix)
                or f"/{prefix}/" in f"/{comparable_filename}/"
                for prefix in normalized_prefixes
            ):
                continue

            for line_element in class_element.findall("./lines/line"):
                line_number = line_element.get("number")
                if line_number is None:
                    continue

                key = (normalized_filename, int(line_number))
                hits = int(line_element.get("hits", "0"))
                line_hits[key] = max(line_hits.get(key, 0), hits)

    total_lines = len(line_hits)
    covered_lines = sum(1 for hits in line_hits.values() if hits > 0)
    return covered_lines, total_lines


def coverage_percentage(covered_lines: int, total_lines: int) -> float:
    if total_lines == 0:
        raise ValueError("Coverage reports did not contain any executable lines.")

    return covered_lines / total_lines * 100


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enforce an aggregate line-coverage threshold from Cobertura reports."
    )
    parser.add_argument(
        "--reports",
        nargs="+",
        required=True,
        help="Cobertura files or recursive glob patterns.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        required=True,
        help="Minimum aggregate line coverage percentage.",
    )
    parser.add_argument(
        "--include-prefix",
        action="append",
        default=[],
        help=(
            "Only include source files below this normalized path prefix. "
            "Repeat the option to include more than one prefix."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_paths = resolve_reports(args.reports)

    if not report_paths:
        print("##vso[task.logissue type=error]No Cobertura coverage reports were found.")
        return 2

    try:
        covered_lines, total_lines = aggregate_line_coverage(
            report_paths, args.include_prefix
        )
        percentage = coverage_percentage(covered_lines, total_lines)
    except (ET.ParseError, OSError, ValueError) as error:
        print(f"##vso[task.logissue type=error]{error}")
        return 2

    print(
        "Aggregate line coverage: "
        f"{percentage:.2f}% ({covered_lines}/{total_lines} lines) "
        f"across {len(report_paths)} report(s)."
    )
    print(f"Required line coverage: {args.threshold:.2f}%")

    if percentage < args.threshold:
        print(
            "##vso[task.logissue type=error]"
            f"Line coverage {percentage:.2f}% is below the "
            f"required {args.threshold:.2f}%."
        )
        return 1

    print("Coverage quality gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
