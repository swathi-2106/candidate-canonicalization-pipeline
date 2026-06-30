"""CLI commands for the candidate canonicalization pipeline."""
import json
import sys

import click

from src.pipeline.config import PipelineConfig
from src.pipeline.orchestrator import PipelineOrchestrator
from src.utils.logger import setup_logger


@click.group()
def cli():
    """Candidate Profile Canonicalization Pipeline - CLI."""
    pass


@cli.command()
@click.option("--csv-dir", type=click.Path(file_okay=False), help="Directory containing recruiter CSV files.")
@click.option("--resume-dir", type=click.Path(file_okay=False), help="Directory containing resume PDF files.")
@click.option("--output-dir", type=click.Path(file_okay=False), default=None, help="Directory to write outputs to.")
@click.option("--format", "formats", multiple=True, type=click.Choice(["json", "csv", "excel"]), default=(), help="Output format(s); repeat flag for multiple. Defaults to config file's output_formats, or 'json' if unset.")
@click.option("--config", "config_path", type=click.Path(exists=True, dir_okay=False), help="Path to YAML/JSON pipeline config file.")
@click.option("--merge-priority", type=click.Choice(["CSV", "RESUME"]), default=None, help="Which source wins unspecified field conflicts.")
@click.option("--column-mapping", type=click.Path(exists=True, dir_okay=False), help="JSON file of {csv_header: canonical_field} overrides.")
@click.option("--projection", type=click.Path(exists=True, dir_okay=False), help="JSON file defining a custom projection spec.")
@click.option("--schema", type=click.Path(exists=True, dir_okay=False), help="JSON schema file to validate output profiles against.")
@click.option("--parallel/--no-parallel", default=None, help="Enable/disable concurrent file processing.")
@click.option("--max-workers", type=int, default=None)
@click.option("--validate-only", is_flag=True, help="Parse and validate inputs, then write validation reports only.")
@click.option("--dry-run", is_flag=True, help="Run the pipeline without writing output artifacts.")
@click.option("-v", "--verbose", is_flag=True, help="Verbose (DEBUG) console logging.")
@click.option("-q", "--quiet", is_flag=True, help="Quiet console logging (errors only).")
@click.option("--log-file", type=click.Path(dir_okay=False), default=None)
def run(csv_dir, resume_dir, output_dir, formats, config_path, merge_priority, column_mapping,
        projection, schema, parallel, max_workers, validate_only, dry_run, verbose, quiet, log_file):
    """Run the full canonicalization pipeline on a CSV directory and/or resume directory."""
    overrides = {
        "csv_input_dir": csv_dir,
        "resume_input_dir": resume_dir,
        "output_dir": output_dir,
        "output_formats": list(formats) if formats else None,
        "merge_priority": merge_priority,
        "schema_file": schema,
        "parallel": parallel,
        "max_workers": max_workers,
        "verbose": verbose if verbose else None,
        "quiet": quiet if quiet else None,
        "log_file": log_file,
        "validate_only": validate_only if validate_only else None,
        "dry_run": dry_run if dry_run else None,
    }
    if column_mapping:
        with open(column_mapping, "r", encoding="utf-8") as f:
            overrides["column_mapping"] = json.load(f)
    if projection:
        with open(projection, "r", encoding="utf-8") as f:
            overrides["projection_spec"] = json.load(f)

    config = PipelineConfig.load(config_path=config_path, overrides=overrides)
    logger = setup_logger(
        verbose=config.verbose,
        quiet=config.quiet,
        log_file=None if config.dry_run else config.log_file,
    )

    if not config.csv_input_dir and not config.resume_input_dir:
        click.echo("Error: at least one of --csv-dir/--resume-dir or a config file specifying csv_input_dir/resume_input_dir must be provided.", err=True)
        sys.exit(1)

    logger.info("Starting pipeline run | csv_dir=%s resume_dir=%s output_dir=%s formats=%s",
                config.csv_input_dir, config.resume_input_dir, config.output_dir, config.output_formats)

    orchestrator = PipelineOrchestrator(config)
    try:
        report = orchestrator.run()
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    click.echo("")
    if config.dry_run:
        click.echo("Dry run complete: no output artifacts were written.")
        click.echo(f"  Files processed: {report['input_summary'].get('files_processed', 0)}")
        click.echo(f"  Candidate profiles: {report['output_summary']['total_profiles']}")
        click.echo(f"  Merges: {report['output_summary'].get('merge_count', 0)}")
        click.echo(f"  Validation: {report['output_summary']['valid_profiles']} valid, {report['output_summary']['invalid_profiles']} invalid")
        click.echo(f"  Average confidence: {report['output_summary']['average_confidence']}")
    elif config.validate_only:
        click.echo(f"Validation complete: {report['output_summary']['total_profiles']} profile(s) checked "
                   f"({report['output_summary']['valid_profiles']} valid, {report['output_summary']['invalid_profiles']} invalid).")
        click.echo(f"  Validation report written to: {config.output_dir}")
    else:
        click.echo(f"Pipeline complete: {report['output_summary']['total_profiles']} profile(s) generated "
                   f"({report['output_summary']['valid_profiles']} valid, {report['output_summary']['invalid_profiles']} invalid).")
        click.echo(f"  Average confidence: {report['output_summary']['average_confidence']}")
        click.echo(f"  Outputs written to: {config.output_dir}")
    if report["error_count"]:
        click.echo(f"  Warning: {report['error_count']} error(s) occurred during processing")
        for e in report["errors"][:10]:
            click.echo(f"    - {e}")


@cli.command()
@click.argument("csv_file", type=click.Path(exists=True, dir_okay=False))
def inspect_csv(csv_file):
    """Quickly preview how a CSV file's columns would be mapped, without running the full pipeline."""
    from src.parsers.csv_parser import CSVParser
    parser = CSVParser()
    profiles = parser.parse(csv_file)
    click.echo(f"Parsed {len(profiles)} row(s) from {csv_file}")
    for p in profiles[:5]:
        click.echo(f"  - {p.name.value} <{p.email.value}>")
    if parser.errors:
        click.echo(f"\n{len(parser.errors)} row error(s):")
        for e in parser.errors[:10]:
            click.echo(f"  - {e}")


@cli.command()
@click.argument("pdf_file", type=click.Path(exists=True, dir_okay=False))
def inspect_resume(pdf_file):
    """Quickly preview extraction results for a single resume PDF."""
    from src.parsers.resume_parser import ResumeParser
    parser = ResumeParser()
    profile = parser.parse(pdf_file)
    if not profile:
        click.echo(f"Failed to parse {pdf_file}: {parser.errors}")
        return
    click.echo(json.dumps(profile.to_dict(), indent=2, default=str))


def main():
    cli()


if __name__ == "__main__":
    main()
