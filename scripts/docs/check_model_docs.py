#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


README_SECTIONS = (
    "Status",
    "Scientific Scope",
    "Canonical Configs",
    "Topology Summary",
    "Numerical Formulation",
    "Parameter Sources and Calibration",
    "Validation State",
    "Run Commands",
    "Reference Outputs",
    "Known Limitations",
    "Documentation Regeneration",
)

IMPLEMENTATION_SECTIONS = (
    "Status",
    "Scope and Canonical Configs",
    "Topology and Naming",
    "Block and Numerical Conventions",
    "Parameter and Unit Conventions",
    "Calibration and Validation Policy",
    "Scenario Policy",
    "Documentation Regeneration",
    "Current Limitations",
)


@dataclass(frozen=True)
class ModelDocs:
    name: str
    configs: tuple[str, ...]


MODELS = (
    ModelDocs(
        name="full_0d",
        configs=(
            "fontan_0d_smoke.jsonc",
            "fontan_0d_baseline.jsonc",
            "fontan_0d_vasodilation.jsonc",
            "fontan_0d_fenestration.jsonc",
            "fontan_0d_lpa_obstruction.jsonc",
        ),
    ),
    ModelDocs(
        name="quasi_0d_1d",
        configs=(
            "fontan_quasi_smoke.jsonc",
            "fontan_quasi_baseline.jsonc",
            "fontan_quasi_vasodilation.jsonc",
            "fontan_quasi_fenestration.jsonc",
            "fontan_quasi_lpa_obstruction.jsonc",
        ),
    ),
    ModelDocs(
        name="coupled_0d_1d",
        configs=(
            "fontan_coupled_0d_1d_smoke.jsonc",
            "fontan_coupled_0d_1d_baseline.jsonc",
            "fontan_coupled_0d_1d_vasodilation.jsonc",
            "fontan_coupled_0d_1d_fenestration.jsonc",
            "fontan_coupled_0d_1d_lpa_obstruction.jsonc",
        ),
    ),
)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def has_section(text: str, title: str) -> bool:
    return f"## {title}\n" in text or f"## {title}\r\n" in text


def check_file(errors: list[str], path: Path) -> None:
    if not path.exists():
        errors.append(f"missing {rel(path)}")
    elif not path.is_file():
        errors.append(f"not a file: {rel(path)}")


def check_pdf(errors: list[str], path: Path) -> None:
    check_file(errors, path)
    if path.exists() and path.is_file() and not path.read_bytes().startswith(b"%PDF"):
        errors.append(f"not a PDF: {rel(path)}")


def check_markdown_sections(
    errors: list[str],
    path: Path,
    sections: tuple[str, ...],
) -> None:
    check_file(errors, path)
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    missing = [section for section in sections if not has_section(text, section)]
    if missing:
        errors.append(f"{rel(path)} missing sections: {', '.join(missing)}")


def check_model(model: ModelDocs) -> list[str]:
    errors: list[str] = []
    model_dir = ROOT / "models" / model.name
    docs_dir = model_dir / "docs"

    for required_dir in ("configs", "calibration", "reference_outputs", "docs"):
        path = model_dir / required_dir
        if not path.exists() or not path.is_dir():
            errors.append(f"missing directory {rel(path)}")

    readme = model_dir / "README.md"
    implementation = docs_dir / "implementation_notes.md"
    schematic_svg = docs_dir / f"{model.name}_schematic.svg"
    schematic_png = docs_dir / f"{model.name}_schematic.png"
    technical_md = docs_dir / f"{model.name}_technical_reference.md"
    technical_pdf = docs_dir / f"{model.name}_technical_reference.pdf"

    check_markdown_sections(errors, readme, README_SECTIONS)
    check_markdown_sections(errors, implementation, IMPLEMENTATION_SECTIONS)
    check_file(errors, schematic_svg)
    check_file(errors, schematic_png)
    check_file(errors, technical_md)
    check_pdf(errors, technical_pdf)

    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        for config in model.configs:
            config_path = model_dir / "configs" / config
            check_file(errors, config_path)
            if config not in text:
                errors.append(f"{rel(readme)} does not mention config {config}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=[model.name for model in MODELS])
    args = parser.parse_args()

    errors: list[str] = []
    top_index = ROOT / "models" / "README.md"
    check_file(errors, top_index)

    for model in MODELS:
        if args.model is not None and model.name != args.model:
            continue
        errors.extend(check_model(model))

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    checked = args.model if args.model is not None else "all model families"
    print(f"model documentation check passed for {checked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
