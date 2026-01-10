# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Factory init command for scaffolding new projects.

This module implements the 'factory init' command that creates new
AWS API Factory projects from the starter template.

Example:
    $ factory init my-api
    $ factory init my-api --profile scalable
    $ factory init  # Uses current directory name

"""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 - intentional use for git/pre-commit commands
from pathlib import Path

import click

from aws_api_factory.cli.utils import (
    CLIError,
    console,
    ensure_directory,
    get_verbose_context,
    print_error,
    print_info,
    print_step,
    print_success,
    print_warning,
)


def get_starter_template_path() -> Path:
    """Get the path to the starter template directory.

    Returns:
        Path to the starter template.

    Raises:
        CLIError: If the template directory cannot be found.
    """
    # Try to find the template relative to the package
    package_dir = Path(__file__).parent.parent.parent
    template_path = package_dir.parent.parent / "starter"

    if template_path.exists():
        return template_path

    # Try to find it relative to the installed package
    import aws_api_factory

    package_root = Path(aws_api_factory.__file__).parent.parent.parent
    template_path = package_root / "starter"

    if template_path.exists():
        return template_path

    raise CLIError(
        "Starter template not found",
        suggestion="The starter template should be included with the package. "
        "If you installed from source, ensure the 'starter' directory exists.",
    )


def copy_template(
    template_dir: Path,
    target_dir: Path,
    project_name: str,
    profile: str,
    verbose: bool = False,
) -> list[Path]:
    """Copy template files to the target directory with replacements.

    Args:
        template_dir: Source template directory.
        target_dir: Destination directory.
        project_name: Name of the new project.
        profile: Profile to use (minimal or scalable).
        verbose: Whether to print verbose output.

    Returns:
        List of created file paths.
    """
    created_files: list[Path] = []

    # Define replacements for template files
    replacements = {
        "my-api": project_name,
        "profile: minimal": f"profile: {profile}",
    }

    # Files/directories to skip
    skip_patterns = {
        "__pycache__",
        ".pyc",
        ".git",
        ".venv",
        "cdk.out",
        "*.egg-info",
    }

    def should_skip(path: Path) -> bool:
        """Check if a path should be skipped."""
        for pattern in skip_patterns:
            if pattern.startswith("*"):
                if path.name.endswith(pattern[1:]):
                    return True
            elif pattern in str(path):
                return True
        return False

    def copy_with_replacements(src: Path, dst: Path) -> None:
        """Copy a file, applying text replacements for text files."""
        # Check if it's a text file
        text_extensions = {".py", ".yaml", ".yml", ".md", ".txt", ".json", ".toml"}
        is_text = src.suffix.lower() in text_extensions or src.name in {
            "Dockerfile",
            ".gitignore",
            "requirements.txt",
        }

        if is_text:
            try:
                content = src.read_text()
                for old, new in replacements.items():
                    content = content.replace(old, new)
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(content)
            except UnicodeDecodeError:
                # Binary file, just copy
                shutil.copy2(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    # Walk the template directory
    for src_path in template_dir.rglob("*"):
        if should_skip(src_path):
            continue

        if src_path.is_file():
            rel_path = src_path.relative_to(template_dir)
            dst_path = target_dir / rel_path

            copy_with_replacements(src_path, dst_path)
            created_files.append(dst_path)

            if verbose:
                console.print(f"  Created: {rel_path}", style="dim")

    return created_files


def init_git_repository(project_dir: Path, verbose: bool = False) -> bool:
    """Initialize a git repository in the project directory.

    Args:
        project_dir: The project directory.
        verbose: Whether to print verbose output.

    Returns:
        True if successful, False otherwise.
    """
    try:
        # Check if git is available
        git_path = shutil.which("git")
        if not git_path:
            return False

        # Check if already a git repo
        if (project_dir / ".git").exists():
            if verbose:
                print_info("Git repository already exists")
            return True

        # Initialize git repo
        result = subprocess.run(  # nosec B603, B607 - trusted git command
            ["git", "init"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            # Create initial .gitignore if it doesn't exist
            gitignore_path = project_dir / ".gitignore"
            if not gitignore_path.exists():
                gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv/
venv/
ENV/

# AWS CDK
cdk.out/
.cdk.staging/
cdk.context.json

# IDE
.idea/
.vscode/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Secrets
.env
.secrets
*.pem
*.key

# OS
.DS_Store
Thumbs.db
"""
                gitignore_path.write_text(gitignore_content)

            if verbose:
                print_info("Git repository initialized")
            return True

    except Exception as e:
        if verbose:
            print_warning(f"Failed to initialize git: {e}")

    return False


def setup_pre_commit(project_dir: Path, verbose: bool = False) -> bool:
    """Set up pre-commit hooks in the project.

    Args:
        project_dir: The project directory.
        verbose: Whether to print verbose output.

    Returns:
        True if successful, False otherwise.
    """
    try:
        # Check if pre-commit is available
        precommit_path = shutil.which("pre-commit")
        if not precommit_path:
            if verbose:
                print_info("pre-commit not installed, skipping hook setup")
            return False

        # Check if .pre-commit-config.yaml exists
        config_path = project_dir / ".pre-commit-config.yaml"
        if not config_path.exists():
            # Create a basic pre-commit config
            config_content = """# Pre-commit hooks for AWS API Factory project
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 24.1.1
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.7
    hooks:
      - id: bandit
        args: ["-c", "pyproject.toml"]
        additional_dependencies: ["bandit[toml]"]
"""
            config_path.write_text(config_content)

        # Install pre-commit hooks
        result = subprocess.run(  # nosec B603, B607 - trusted pre-commit command
            ["pre-commit", "install"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            if verbose:
                print_info("Pre-commit hooks installed")
            return True

    except Exception as e:
        if verbose:
            print_warning(f"Failed to set up pre-commit: {e}")

    return False


def create_virtual_environment(project_dir: Path, verbose: bool = False) -> bool:
    """Create a Python virtual environment.

    Args:
        project_dir: The project directory.
        verbose: Whether to print verbose output.

    Returns:
        True if successful, False otherwise.
    """
    venv_path = project_dir / ".venv"
    if venv_path.exists():
        if verbose:
            print_info("Virtual environment already exists")
        return True

    try:
        import venv

        venv.create(venv_path, with_pip=True)
        if verbose:
            print_info("Virtual environment created")
        return True
    except Exception as e:
        if verbose:
            print_warning(f"Failed to create virtual environment: {e}")
        return False


@click.command("init")
@click.argument("project_name", required=False)
@click.option(
    "--profile",
    "-p",
    type=click.Choice(["minimal", "scalable"]),
    default="minimal",
    help="Profile to use for the project (minimal or scalable).",
)
@click.option(
    "--directory",
    "-d",
    type=click.Path(),
    default=None,
    help="Directory to create the project in (defaults to project name).",
)
@click.option(
    "--no-git",
    is_flag=True,
    default=False,
    help="Skip git repository initialization.",
)
@click.option(
    "--no-venv",
    is_flag=True,
    default=False,
    help="Skip virtual environment creation.",
)
@click.pass_context
def init(
    ctx: click.Context,
    project_name: str | None,
    profile: str,
    directory: str | None,
    no_git: bool,
    no_venv: bool,
) -> None:
    """Scaffold a new AWS API Factory project.

    Creates a new project directory with the starter template,
    including factory.yaml configuration and example services.

    \b
    Examples:
        factory init my-api
        factory init my-api --profile scalable
        factory init my-api --directory ./projects/my-api
        factory init  # Uses current directory

    If PROJECT_NAME is not provided, the current directory name will be used.
    """
    verbose = get_verbose_context(ctx)

    # Determine project name and directory
    if project_name is None:
        project_name = Path.cwd().name
        target_dir = Path.cwd()
        using_current_dir = True
    else:
        target_dir = Path(directory) if directory else Path.cwd() / project_name
        using_current_dir = False

    # Validate project name
    if not project_name or not project_name.replace("-", "").replace("_", "").isalnum():
        print_error(
            "Invalid project name",
            suggestion="Project name must contain only letters, numbers, hyphens, and underscores.",
        )
        raise SystemExit(1)

    # Check if directory exists and is not empty
    if target_dir.exists() and any(target_dir.iterdir()):
        if not using_current_dir:
            print_error(
                f"Directory '{target_dir}' already exists and is not empty",
                suggestion="Choose a different directory or remove the existing one.",
            )
            raise SystemExit(1)
        else:
            # For current directory, check if factory.yaml already exists
            if (target_dir / "factory.yaml").exists():
                print_error(
                    "A factory.yaml already exists in the current directory",
                    suggestion="Remove the existing factory.yaml or use a different directory.",
                )
                raise SystemExit(1)

    console.print(
        f"\n[bold]Creating new AWS API Factory project:[/bold] [cyan]{project_name}[/cyan]\n"
    )

    total_steps = 4 - int(no_git) - int(no_venv)
    current_step = 0

    # Step 1: Get and copy template
    current_step += 1
    print_step(current_step, total_steps, "Copying starter template...")

    try:
        template_dir = get_starter_template_path()
    except CLIError as e:
        print_error(e.message, e.suggestion)
        raise SystemExit(e.exit_code)

    ensure_directory(target_dir)
    created_files = copy_template(
        template_dir, target_dir, project_name, profile, verbose
    )
    print_success(f"Created {len(created_files)} files")

    # Step 2: Initialize git repository
    if not no_git:
        current_step += 1
        print_step(current_step, total_steps, "Initializing git repository...")
        if init_git_repository(target_dir, verbose):
            print_success("Git repository initialized")
        else:
            print_warning("Git initialization skipped (git not available)")

    # Step 3: Create virtual environment
    if not no_venv:
        current_step += 1
        print_step(current_step, total_steps, "Creating virtual environment...")
        if create_virtual_environment(target_dir, verbose):
            print_success("Virtual environment created at .venv/")
        else:
            print_warning("Virtual environment creation skipped")

    # Step 4: Print next steps
    current_step += 1
    print_step(current_step, total_steps, "Done!")

    console.print()
    console.print("[bold green]✓ Project created successfully![/bold green]")
    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print()

    if not using_current_dir:
        console.print(f"  1. cd {target_dir}")
        console.print("  2. source .venv/bin/activate")
        console.print("  3. pip install -e .")
    else:
        console.print("  1. source .venv/bin/activate")
        console.print("  2. pip install -e .")

    console.print()
    console.print("  Then:")
    console.print("  - Edit [path]factory.yaml[/path] to configure your API")
    console.print("  - Add your services in [path]src/services/[/path]")
    console.print("  - Run [command]factory validate[/command] to check configuration")
    console.print("  - Run [command]factory deploy dev[/command] to deploy")
    console.print()
