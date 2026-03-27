#!/usr/bin/env python3
"""PolyWatch Data Quality Report CLI."""
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from data_quality import generate_report, format_markdown


def main():
    parser = argparse.ArgumentParser(description="Generate PolyWatch data quality report")
    parser.add_argument("--output", "-o", type=str, help="Output file path (default: stdout)")
    parser.add_argument("--format", "-f", type=str, choices=["markdown", "json"],
                        default="markdown", help="Output format")
    args = parser.parse_args()

    report = generate_report()

    if args.format == "json":
        text = json.dumps(report, indent=2, default=str)
    else:
        text = format_markdown(report)

    if args.output:
        with open(args.output, "w") as f:
            f.write(text)
        print(f"Report written to {args.output}")
    else:
        print(text)


if __name__ == "__main__":
    main()
