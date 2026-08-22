"""The skillforge command line."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import click
import yaml

from skillforge import __version__, hooks
from skillforge import config as config_module
from skillforge import lock as lock_module
from skillforge import plan as plan_module
from skillforge.errors import ConfigError, DriftError, SkillforgeError
from skillforge.lint import lint_tree
from skillforge.render import base_directory, build, load_layered_config

STARTER = """version: 1

sources: {}

skills: []

shared_params: {}

targets:
  claude-code: {}
  agents-md: {}

output: .agents/skills
"""


def _root(root: str | None) -> Path:
    return Path(root or ".").resolve()


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="skillforge")
def main() -> None:
    """Compose portable AI agent skills from a versioned upstream library."""


@main.command()
@click.option("--root", default=None, help="Repository root (defaults to the current directory).")
def init(root: str | None) -> None:
    """Write a starter skillforge.yaml."""
    target = _root(root) / config_module.CONFIG_NAME
    if target.exists():
        raise ConfigError(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(STARTER, encoding="utf-8")
    click.echo(f"wrote {target}")


@main.command(name="build")
@click.option("--root", default=None, help="Repository root.")
def build_command(root: str | None) -> None:
    """Render every configured skill and write the harness outputs."""
    where = _root(root)
    result = build(where)
    written = plan_module.apply(result.plan, where)
    lock_module.dump(result.lock, where)
    click.echo(f"built {len(result.skills)} skill(s) into {result.config.output}")
    for path in written:
        click.echo(f"  {path}")


@main.command()
@click.option("--root", default=None, help="Repository root.")
def check(root: str | None) -> None:
    """Fail if committed output does not match what a build would produce."""
    where = _root(root)
    result = build(where)
    problems = plan_module.diff(result.plan, where)
    committed = lock_module.load(where)
    if committed.outputs != result.lock.outputs:
        problems.append(f"stale: {lock_module.LOCK_NAME} does not match the current build")
    if problems:
        raise DriftError(
            "committed output is out of date. Run `skillforge build` and commit the result:\n  "
            + "\n  ".join(problems)
        )
    click.echo(f"up to date: {len(result.skills)} skill(s), {len(result.plan.files)} file(s)")


@main.command(name="lint")
@click.option("--root", default=None, help="Repository root.")
@click.option("--skills", "skills_dir", default="skills", help="Directory of base skills.")
@click.option("--strict", is_flag=True, help="Treat warnings as failures.")
def lint_command(root: str | None, skills_dir: str, strict: bool) -> None:
    """Validate the base skills authored in this repository."""
    warnings = lint_tree(_root(root) / skills_dir)
    for warning in warnings:
        click.echo(f"warning: {warning}", err=True)
    if warnings and strict:
        raise SkillforgeError(f"{len(warnings)} warning(s) with --strict")
    click.echo(f"lint passed with {len(warnings)} warning(s)")


@main.command()
@click.argument("aliases", nargs=-1)
@click.option("--root", default=None, help="Repository root.")
def update(aliases: tuple[str, ...], root: str | None) -> None:
    """Re-resolve upstream refs, then rebuild. With no argument, updates every source."""
    where = _root(root)
    before = lock_module.load(where)
    refresh = set(aliases) if aliases else None
    if refresh is None:
        config, _ = load_layered_config(where, before)
        refresh = set(config.sources)
    result = build(where, refresh=refresh)
    plan_module.apply(result.plan, where)
    lock_module.dump(result.lock, where)
    for alias, entry in sorted(result.lock.sources.items()):
        old = before.commit_for(alias)
        if old == entry["commit"]:
            click.echo(f"{alias}: unchanged at {entry['commit'][:12]}")
        else:
            click.echo(f"{alias}: {(old or 'none')[:12]} -> {entry['commit'][:12]}")


@main.command()
@click.argument("name")
@click.option("--root", default=None, help="Repository root.")
@click.option("--into", default="skills", help="Local directory to copy the base skill into.")
def eject(name: str, root: str | None, into: str) -> None:
    """Copy an imported skill into this repo and cut its link to upstream.

    The config is rewritten with PyYAML, so comments and formatting in
    skillforge.yaml are normalised.
    """
    where = _root(root)
    config, resolved = load_layered_config(where, lock_module.load(where))
    matches = [s for s in config.skills if s.name == name]
    if not matches:
        known = ", ".join(sorted(s.name for s in config.skills)) or "none"
        raise ConfigError(f"no configured skill named `{name}` (configured: {known})")
    request = matches[0]
    if request.is_local:
        raise ConfigError(f"skill `{name}` is already local ({request.ref})")

    destination = where / into / name
    if destination.exists():
        raise ConfigError(f"{destination} already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(base_directory(request, config, resolved), destination)

    path = where / config_module.CONFIG_NAME
    raw = config_module.load_raw(path)
    for entry in raw.get("skills") or []:
        if (entry.get("as") or Path(entry["from"]).name) == name:
            entry["from"] = f"./{into}/{name}"
            entry.pop("patches", None)
            break
    path.write_text(
        yaml.safe_dump(raw, sort_keys=False, default_flow_style=False), encoding="utf-8"
    )
    click.echo(f"ejected `{name}` into {destination}")
    click.echo(
        "patches were dropped; they are now part of the copied skill's history to re-apply by hand"
    )
    click.echo("run `skillforge build` to regenerate")


@main.command(name="add")
@click.argument("ref")
@click.option("--root", default=None, help="Repository root.")
@click.option("--as", "alias", default=None, help="Local name for the skill.")
def add_command(ref: str, root: str | None, alias: str | None) -> None:
    """Append a skill to skillforge.yaml.

    The config is rewritten with PyYAML, so comments and formatting are normalised.
    """
    path = _root(root) / config_module.CONFIG_NAME
    raw = config_module.load_raw(path)
    name = alias or Path(ref).name
    entries = raw.setdefault("skills", []) or []
    if any((e.get("as") or Path(e["from"]).name) == name for e in entries):
        raise ConfigError(f"skill `{name}` is already configured")
    entry: dict = {"from": ref}
    if alias:
        entry["as"] = alias
    entries.append(entry)
    raw["skills"] = entries
    path.write_text(
        yaml.safe_dump(raw, sort_keys=False, default_flow_style=False), encoding="utf-8"
    )
    click.echo(f"added `{name}`; run `skillforge build` to render it")


@main.command()
@click.option("--root", default=None, help="Repository root.")
def ci(root: str | None) -> None:
    """Everything that must pass before a commit lands: lint, then drift check."""
    where = _root(root)
    skills_dir = where / "skills"
    if skills_dir.is_dir():
        for warning in lint_tree(skills_dir):
            click.echo(f"warning: {warning}", err=True)
    result = build(where)
    problems = plan_module.diff(result.plan, where)
    committed = lock_module.load(where)
    if committed.outputs != result.lock.outputs:
        problems.append(f"stale: {lock_module.LOCK_NAME} does not match the current build")
    if problems:
        raise DriftError(
            "run `skillforge build` and commit the result:\n  " + "\n  ".join(problems)
        )
    click.echo("ci passed")


@main.command(name="install-hooks")
@click.option("--root", default=None, help="Repository root.")
def install_hooks(root: str | None) -> None:
    """Install pre-commit and pre-push hooks that run the local CI."""
    for path in hooks.install(_root(root)):
        click.echo(f"installed {path}")


def run() -> int:
    try:
        main.main(standalone_mode=False)
    except SkillforgeError as error:
        click.echo(f"error: {error}", err=True)
        return 1
    except click.ClickException as error:
        error.show()
        return error.exit_code
    except click.exceptions.Abort:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(run())
