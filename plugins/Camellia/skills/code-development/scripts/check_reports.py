#!/usr/bin/env python3
"""Run all code-development report check groups with one shared input context."""

import sys
from pathlib import Path

# Keep sibling modules available for direct execution, including Python -I.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from report_common import AREAS, Context, run_checks, run_cli
import check_report_structure
import check_completion_records
import check_work_bundles
import check_report_links
import check_report_diagrams

CHECKS = [
    ('structure', check_report_structure.check),
    ('completion', check_completion_records.check),
    ('bundles', check_work_bundles.check),
    ('links', check_report_links.check),
    ('diagrams', check_report_diagrams.check),
]


class Checker(Context):
    def run(self):
        return run_checks(self, CHECKS)


def main(argv=None):
    return run_cli(CHECKS, argv)


if __name__ == '__main__':
    sys.exit(main())
