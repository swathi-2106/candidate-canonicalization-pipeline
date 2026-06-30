#!/usr/bin/env python3
"""Entry point: `python main.py run --csv-dir ... --resume-dir ...`"""
from src.cli.commands import cli

if __name__ == "__main__":
    cli()
