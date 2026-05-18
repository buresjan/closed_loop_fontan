#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ModelSpec:
    name: str
    title: str
    status: str
    baseline_config: Path | None
    scenario_glob: str | None
    overview: tuple[str, ...]
    accepted_components: tuple[str, ...]
    limitations: tuple[str, ...]


MODEL_SPECS = {
    "full_0d": ModelSpec(
        name="full_0d",
        title="Full 0-D Closed-Loop Fontan Model Technical Reference",
        status="Accepted full 0-D reference model.",
        baseline_config=ROOT / "models/full_0d/configs/fontan_0d_baseline.jsonc",
        scenario_glob="configs/fontan_0d_*.jsonc",
        overview=(
            "This model is the accepted closed-loop 0-D reference circulation.",
            "It uses a PhysioBlocks active spherical single ventricle, an active "
            "time-varying-elastance atrium, R-L valves, lumped vascular "
            "compliances, systemic resistive beds, Fontan conduit elements, "
            "pulmonary RCR beds, and an optional fenestration shunt.",
            "No inlet pressure, outlet pressure, or prescribed inflow boundary "
            "condition drives the baseline circulation.",
        ),
        accepted_components=(
            "active atrium and active spherical ventricle",
            "atrioventricular and aortic valve R-L blocks",
            "ascending aorta, aortic arch, BCA, LCCA, LSA, and DAo tree",
            "upper and lower systemic vascular beds",
            "SVC, IVC, RPA, and LPA Fontan conduit states",
            "right and left pulmonary RCR Windkessel beds",
            "high-resistance baseline fenestration path",
        ),
        limitations=(
            "The model is a calibrated computational development artifact, not "
            "a clinically validated patient-specific simulator.",
            "The aortic and Fontan pathways are lumped 0-D approximations rather "
            "than true spatially resolved 1-D domains.",
            "Scenario files inherit the baseline calibration and are validation "
            "cases, not independently retuned models.",
        ),
    ),
    "quasi_0d_1d": ModelSpec(
        name="quasi_0d_1d",
        title="Quasi 0-D/1-D Fontan Model Technical Reference",
        status="Accepted PhysioBlocks-only quasi 0-D/1-D model.",
        baseline_config=ROOT / "models/quasi_0d_1d/configs/fontan_quasi_baseline.jsonc",
        scenario_glob="configs/fontan_quasi_*.jsonc",
        overview=(
            "This model keeps the accepted full 0-D heart, atrium, valves, "
            "systemic beds, pulmonary RCR beds, and fenestration, while replacing "
            "selected aortic and Fontan conduit shortcuts with distributed "
            "R-L-C chains.",
            "It does not contain a nonlinear 1-D PDE solver. Its quasi-1-D "
            "behavior comes from repeated hydraulic R-L links and compliance "
            "states embedded in the closed loop.",
            "The accepted baseline is selected by the frozen quasi-vs-full0D "
            "superiority gate.",
        ),
        accepted_components=(
            "active atrium and active spherical ventricle retained from full 0-D",
            "atrioventricular and aortic valve R-L blocks retained from full 0-D",
            "AAo/arch, DAo, SVC, IVC, RPA, and LPA quasi R-L-C chains",
            "upper and lower systemic vascular beds",
            "right and left pulmonary RCR Windkessel beds",
            "scenario-specific pulmonary vasodilation, fenestration, and LPA "
            "obstruction variants without scenario-specific retuning",
        ),
        limitations=(
            "The model is quasi 0-D/1-D only; wave propagation is approximated "
            "by finite R-L-C chains rather than by a true coupled 1-D solver.",
            "Clinical DAo bed-entry flow remains a soft diagnostic because it "
            "mixes aortic trunk behavior with downstream terminal-load dynamics.",
            "The model is not clinically validated.",
        ),
    ),
    "coupled_0d_1d": ModelSpec(
        name="coupled_0d_1d",
        title="Coupled 0-D/1-D Fontan Model Technical Reference",
        status=(
            "Executable Task 012 prototype with true 1-D aorta and TCPC "
            "segments inserted into the closed loop. The Task 012 baseline "
            "completes 20 s with stability, mass-balance, and periodicity "
            "checks passing; Task 013 calibration is in progress."
        ),
        baseline_config=ROOT / "models/coupled_0d_1d/configs/fontan_coupled_0d_1d_baseline.jsonc",
        scenario_glob="configs/fontan_coupled_0d_1d_*.jsonc",
        overview=(
            "Task 010 provides a local fixed three-cell true 1-D vessel "
            "prototype with area and face-flow states, nonlinear momentum, a "
            "pressure-area wall law, pressure/flow coupling, and tested "
            "Jacobian assembly.",
            "Task 011 provides open-loop reference specifications for aorta, "
            "TCPC, and combined aorta-TCPC 1-D submodels using tracked "
            "Aramburu/Nektar geometry, measured inflows, reference outputs, "
            "clinical comparison targets, and documented validation gates.",
            "Task 012 generates executable closed-loop configs by replacing "
            "selected full 0-D aortic and TCPC shortcut pathways with local "
            "true 1-D finite-volume blocks.",
            "The current Task 012 topology uses a tapered six-cell composite "
            "LPA, a massless aortic total-pressure junction, a massless "
            "wall-pressure-blended dissipative TCPC total-pressure junction, "
            "and a retained calibrated 0-D LSA terminal branch.",
            "The executable closed-loop configs use a log-area state "
            "parameterization, $A = \\exp(g)$, so Newton iterations remain "
            "inside the positive vessel-area domain.",
            "All generated coupled scenarios cap the time step at "
            "$2.5\\times 10^{-4}\\,\\mathrm{s}$ because the inherited full "
            "0-D scenario step is too coarse for the inserted 1-D vessel and "
            "TCPC junction dynamics.",
            "The prototype smoke case and 20 s baseline both run. The 20 s "
            "baseline passes no-NaN, positive-area, TCPC balance, atrium "
            "balance, ventricle balance, and periodicity checks, but the model "
            "is not accepted as calibrated while Task 013 remains in progress.",
        ),
        accepted_components=(
            "0-D heart, atrium, systemic beds, pulmonary beds, and fenestration inherited from full 0-D",
            "validated local fixed three-cell true 1-D vessel numerics prototype",
            "validated open-loop reference specs for aorta, TCPC, and combined aorta-TCPC",
            "generated true 1-D aortic blocks for AAo, thoracic aorta, BCA, and left carotid",
            "generated true 1-D TCPC blocks for SVC, IVC, RPA, LPA I, and LPA II",
            "massless total-pressure junction for the aortic arch split",
            "massless wall-pressure-blended dissipative total-pressure junction for the TCPC confluence",
            "retained full 0-D LSA terminal branch because no patient-specific LSA 1-D geometry is available",
            "explicit residual interface loss blocks preserving full 0-D path resistance not represented by 1-D Poiseuille friction",
        ),
        limitations=(
            "The coupled model is executable and periodic at baseline but not accepted as calibrated or clinically validated.",
            "The aortic total-pressure junction is an algebraic no-loss coupler; the TCPC junction adds branch wall-pressure blending and signed dynamic minor losses but is still not Nektar's full characteristic/Riemann boundary treatment or a 3-D TCPC loss model.",
            "The current smoke run is a startup integration test; it is not a physiological cycle validation.",
            "Task 013 calibration and scenario validation remain in progress.",
        ),
    ),
}


STRUCTURAL_BLOCK_KEYS = {
    "type",
    "model_type",
    "time",
    "flux_type",
    "nodes",
    "submodels",
    "alternative_types",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def model_dir(spec: ModelSpec) -> Path:
    return ROOT / "models" / spec.name


def docs_dir(spec: ModelSpec) -> Path:
    return model_dir(spec) / "docs"


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def markdown_escape(value: str) -> str:
    return value.replace("|", "\\|")


def code(value: str) -> str:
    return "`" + value.replace("`", "\\`") + "`"


def format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.12g}"
    if isinstance(value, (int, str)):
        return str(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def nodes_text(block: dict[str, Any]) -> str:
    nodes = block.get("nodes", {})
    if not isinstance(nodes, dict) or not nodes:
        return "-"
    return "; ".join(f"{idx}: {node}" for idx, node in sorted(nodes.items()))


def block_parameter_text(
    block_name: str,
    block: dict[str, Any],
    parameters: dict[str, Any],
) -> str:
    entries: list[str] = []
    for key, value in block.items():
        if key in STRUCTURAL_BLOCK_KEYS:
            continue
        if isinstance(value, str) and value in parameters:
            entries.append(f"{key} -> {value}")
        elif isinstance(value, str):
            entries.append(f"{key} = {value}")
        elif isinstance(value, (int, float, bool)):
            entries.append(f"{key} = {format_value(value)}")

    prefix = f"{block_name}."
    for parameter_name in sorted(parameters):
        if parameter_name.startswith(prefix) and parameter_name not in {
            part.split(" -> ")[-1] for part in entries if " -> " in part
        }:
            entries.append(parameter_name)

    return "; ".join(entries) if entries else "-"


def scenario_files(spec: ModelSpec) -> list[Path]:
    if spec.scenario_glob is None:
        return []
    return sorted(model_dir(spec).glob(spec.scenario_glob))


def block_type_counts(cfg: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for block in cfg["net"]["blocks"].values():
        block_type = block.get("model_type", "unknown")
        counts[block_type] = counts.get(block_type, 0) + 1
    return dict(sorted(counts.items()))


def equation_section() -> list[str]:
    return [
        "## Governing Equations",
        "",
        "The sign convention follows PhysioBlocks local block fluxes. For a "
        "two-node flow element, local node 1 is the first node listed in the "
        "config and local node 2 is the second node listed in the config.",
        "",
        "### Nodal Conservation",
        "",
        "At every pressure node, the algebraic/differential network residual is "
        "the sum of all block flux contributions attached to that node:",
        "",
        r"$$\sum_{b \in \mathcal{B}(i)} Q_{b,i} = 0.$$",
        "",
        "Storage blocks contribute pressure derivatives to this same residual, "
        "so closed-loop volume conservation is enforced through the connected "
        "block equations rather than through prescribed boundary flow.",
        "",
        "### Passive Compliance Block",
        "",
        "For a `c_block` at pressure node `P` with capacitance `C`:",
        "",
        r"$$Q = -C \frac{dP}{dt}.$$",
        "",
        "The saved stored volume is proportional to pressure in the local linear "
        "compliance approximation:",
        "",
        r"$$V = C P.$$",
        "",
        "### Pure RC Resistor Convention",
        "",
        "This repository uses `rc_block` with zero capacitance as a pure "
        "resistive link. PhysioBlocks defines the local fluxes as:",
        "",
        r"$$Q_1 = \frac{P_2 - P_1}{R},$$",
        "",
        r"$$Q_2 = \frac{P_1 - P_2}{R} - C \frac{dP_2}{dt}.$$",
        "",
        "When `C = 0`, the block is used as a pure resistor. To represent an "
        "upstream-to-downstream path with positive physical flow from upstream "
        "to downstream, the configs assign local node 2 to the upstream pressure "
        "and local node 1 to the downstream pressure.",
        "",
        "### Hydraulic R-L Link",
        "",
        "The local quasi-vessel R-L element uses positive internal flow from "
        "local node 1 to local node 2:",
        "",
        r"$$L \frac{dQ}{dt} + RQ = P_1 - P_2,$$",
        "",
        r"$$Q_1 = -Q,\qquad Q_2 = Q.$$",
        "",
        "This is the repeated segment equation used by the quasi 0-D/1-D chains.",
        "",
        "### Valve R-L Block",
        "",
        "The R-L valve block has local positive flow from node 1 to node 2 and "
        "switches conductance according to flow direction:",
        "",
        r"$$L \frac{dQ}{dt} + P_2 - P_1 + R(Q)Q = 0,$$",
        "",
        r"$$R(Q) = \begin{cases}1/G_f,& Q>0,\\ 1/G_b,& Q<0,\end{cases}$$",
        "",
        r"$$Q_1=-Q,\qquad Q_2=Q.$$",
        "",
        "`G_f` is the forward conductance and `G_b` is the backward conductance.",
        "",
        "### Pulmonary RCR Windkessel",
        "",
        "For an `rcr_block` with inlet pressure `P_1`, outlet pressure `P_2`, "
        "middle pressure `P_m`, proximal resistance `R_1`, distal resistance "
        "`R_2`, and compliance `C`:",
        "",
        r"$$Q_1 = \frac{P_m - P_1}{R_1},$$",
        "",
        r"$$Q_2 = \frac{P_m - P_2}{R_2},$$",
        "",
        r"$$\frac{P_1 - P_m}{R_1} + \frac{P_2 - P_m}{R_2} - C\frac{dP_m}{dt}=0.$$",
        "",
        "### Active Atrium",
        "",
        "The active atrium is a one-node time-varying elastance chamber:",
        "",
        r"$$E(t) = E_{min} + (E_{max}-E_{min})a(t),$$",
        "",
        r"$$V_a(t) = V_{0,a} + \frac{P_a(t)-P_{ext}}{E(t)},$$",
        "",
        r"$$Q_a = -\frac{dV_a}{dt}.$$",
        "",
        "The activation `a(t)` is a raised-cosine pulse over the configured "
        "start, peak, and end phase of the cardiac cycle.",
        "",
        "### Spherical Ventricular Cavity",
        "",
        "The active ventricular cavity stores volume through the spherical "
        "cavity displacement `y`, reference radius `R_0`, and wall thickness "
        "`d_0`:",
        "",
        r"$$V(y)=\frac{4\pi}{3}\left[R_0\left(1+\frac{y}{R_0}\right)"
        r"-\frac{d_0}{2\left(1+\frac{y}{R_0}\right)^2}\right]^3,$$",
        "",
        r"$$Q_v = -\frac{dV(y)}{dt}.$$",
        "",
        "The pressure-displacement relation comes from the configured "
        "PhysioBlocks spherical dynamics, velocity law, passive rheology, and "
        "active macro-Huxley submodels. The corresponding free parameters are "
        "listed in the parameter inventory below with the `cavity.*` prefix.",
        "",
    ]


def topology_section(spec: ModelSpec, cfg: dict[str, Any] | None) -> list[str]:
    lines = [
        "## Model Construction",
        "",
        "### Scope and Status",
        "",
        spec.status,
        "",
    ]
    for paragraph in spec.overview:
        lines.extend([paragraph, ""])

    schematic = f"{spec.name}_schematic.png"
    if (docs_dir(spec) / schematic).exists():
        lines.extend(
            [
                "### Schematic",
                "",
                f"![{spec.name} schematic]({schematic}){{ width=100% }}",
                "",
            ]
        )

    lines.extend(["### Accepted Components", ""])
    for item in spec.accepted_components:
        lines.append(f"- {item}")
    lines.append("")

    if cfg is None:
        lines.extend(
            [
                "### Executable Config",
                "",
                "No executable baseline config is accepted for this model family yet.",
                "",
            ]
        )
        return lines

    lines.extend(
        [
            "### Authoritative Baseline Config",
            "",
            f"The executable topology and free-parameter values are taken from "
            f"{code(rel(spec.baseline_config))}.",
            "",
            f"- pressure nodes: {len(cfg['net']['nodes'])}",
            f"- blocks/segments: {len(cfg['net']['blocks'])}",
            f"- free parameter entries: {len(cfg['parameters'])}",
            f"- boundary conditions: {len(cfg['net'].get('boundaries_conditions', {}))}",
            "",
        ]
    )

    scenarios = scenario_files(spec)
    if scenarios:
        lines.extend(["### Scenario Configs", ""])
        for path in scenarios:
            lines.append(f"- {code(rel(path))}")
        lines.append("")

    lines.extend(["### Pressure Nodes", ""])
    for node in cfg["net"]["nodes"]:
        lines.append(f"- {code(node)}")
    lines.append("")

    lines.extend(["### Block Type Counts", ""])
    lines.extend(["| Block type | Count |", "|---|---:|"])
    for block_type, count in block_type_counts(cfg).items():
        lines.append(f"| {code(block_type)} | {count} |")
    lines.append("")
    return lines


def quasi_chain_section(cfg: dict[str, Any] | None) -> list[str]:
    if cfg is None:
        return []
    chain_keys = ["aao_arch", "dao", "svc", "ivc", "rpa", "lpa"]
    parameters = cfg["parameters"]
    blocks = cfg["net"]["blocks"]
    rows: list[str] = []
    for key in chain_keys:
        rl_names = sorted(
            name
            for name, block in blocks.items()
            if name.startswith(f"quasi_{key}_rl_")
            and block.get("model_type") == "hydraulic_rl_block"
        )
        if not rl_names:
            continue
        first = blocks[rl_names[0]]["nodes"]["1"]
        last = blocks[rl_names[-1]]["nodes"]["2"]
        r_total = sum(float(parameters[f"{name}.resistance"]) for name in rl_names)
        l_total = sum(float(parameters[f"{name}.inductance"]) for name in rl_names)
        c_total = sum(
            float(value)
            for pname, value in parameters.items()
            if pname.startswith(f"quasi_{key}_c_") and pname.endswith(".capacitance")
        )
        rows.append(
            "| "
            + " | ".join(
                [
                    code(key),
                    f"{code(first)} -> {code(last)}",
                    str(len(rl_names)),
                    f"{r_total:.6g}",
                    f"{l_total:.6g}",
                    f"{c_total:.6g}",
                ]
            )
            + " |"
        )

    if not rows:
        return []
    return [
        "## Quasi Chain Summary",
        "",
        "The accepted quasi chains are assembled from repeated hydraulic R-L "
        "links and downstream compliance states. Total values in this table are "
        "computed from the baseline config.",
        "",
        "| Chain | Path | Segments | Total R ($\\mathrm{Pa\\,s\\,m^{-3}}$) | Total L ($\\mathrm{Pa\\,s^{2}\\,m^{-3}}$) | Total C ($\\mathrm{m^{3}\\,Pa^{-1}}$) |",
        "|---|---|---:|---:|---:|---:|",
        *rows,
        "",
    ]


def segment_inventory_section(cfg: dict[str, Any] | None) -> list[str]:
    lines = [
        "## Segment Inventory",
        "",
    ]
    if cfg is None:
        lines.extend(
            [
                "No executable segment inventory exists yet. The first coupled "
                "model implementation must list every 0-D block, every 1-D "
                "segment, every coupling interface, and every parameter source "
                "in this section before acceptance.",
                "",
            ]
        )
        return lines

    lines.extend(
        [
            "Each row is a block or segment in the accepted baseline config. "
            "The parameter column lists explicit block fields and all config "
            "parameters sharing the block-name prefix.",
            "",
            "| Segment/block | Type | Local nodes | Free-parameter fields |",
            "|---|---|---|---|",
        ]
    )
    parameters = cfg["parameters"]
    for block_name, block in cfg["net"]["blocks"].items():
        lines.append(
            "| "
            + " | ".join(
                [
                    code(block_name),
                    code(block.get("model_type", "unknown")),
                    markdown_escape(nodes_text(block)),
                    markdown_escape(block_parameter_text(block_name, block, parameters)),
                ]
            )
            + " |"
        )
    lines.append("")
    return lines


def free_parameter_section(cfg: dict[str, Any] | None) -> list[str]:
    lines = [
        "## Free Parameters",
        "",
        "Unless a parameter states otherwise in the config, units follow the "
        "repository SI convention: pressure in $\\mathrm{Pa}$, flow in "
        "$\\mathrm{m^{3}\\,s^{-1}}$, resistance in "
        "$\\mathrm{Pa\\,s\\,m^{-3}}$, capacitance in "
        "$\\mathrm{m^{3}\\,Pa^{-1}}$, inertance in "
        "$\\mathrm{Pa\\,s^{2}\\,m^{-3}}$, volume in $\\mathrm{m^{3}}$, "
        "length in $\\mathrm{m}$, and time in $\\mathrm{s}$.",
        "",
    ]
    if cfg is None:
        lines.extend(
            [
                "No executable free-parameter set is accepted yet for this model "
                "family. The future coupled implementation must list every 0-D "
                "parameter, every 1-D material/geometric parameter, every "
                "coupling-interface parameter, and every calibration bound here.",
                "",
            ]
        )
        return lines

    lines.extend(
        [
            "The entries below are the complete `parameters` dictionary from the "
            "authoritative baseline config. Derived-expression entries are shown "
            "as compact JSON.",
            "",
        ]
    )
    for name, value in sorted(cfg["parameters"].items()):
        lines.append(f"- {code(name)} = {code(format_value(value))}")
    lines.append("")
    return lines


def coupled_1d_prototype_section(spec: ModelSpec) -> list[str]:
    if spec.name != "coupled_0d_1d":
        return []
    return [
        "## Local True 1-D Prototype Equations",
        "",
        "Task 010 adds a local fixed three-cell true 1-D vessel prototype in "
        "`fontan_blocks.one_d`. Task 012 also adds a log-area executable "
        "variant for closed-loop coupling and a fixed six-cell tapered "
        "log-area variant for the composite LPA. These forms solve the same "
        "1-D finite-volume equations.",
        "",
        "For vessel length $L$ and $N = 3$ finite-volume cells:",
        "",
        r"$$\Delta x = \frac{L}{3}.$$",
        "",
        "The area states are cell-centered $A_i(t)$ for $i=1,2,3$ and the "
        "flow states are staggered face flows $Q_j(t)$ for $j=0,1,2,3$.",
        "In the closed-loop executable block, the nonlinear state is "
        "$g_i(t) = \\log A_i(t)$ and $A_i(t)=\\exp(g_i(t))$.",
        "",
        "The nonlinear wall law is:",
        "",
        r"$$P(A) = P_{\mathrm{ext}} + \beta(\sqrt{A} - \sqrt{A_0}),$$",
        "",
        "with wave speed:",
        "",
        r"$$c(A) = \sqrt{\frac{A}{\rho}\frac{dP}{dA}}, \quad "
        r"\frac{dP}{dA} = \frac{\beta}{2\sqrt{A}}.$$",
        "",
        "The finite-volume continuity residual is:",
        "",
        r"$$R_{A_i} = \frac{A_i^{n+1}-A_i^n}{\Delta t} + "
        r"\frac{Q_i^{n+1/2}-Q_{i-1}^{n+1/2}}{\Delta x}.$$",
        "",
        "The face momentum residual is:",
        "",
        r"$$R_{Q_j} = \frac{Q_j^{n+1}-Q_j^n}{\Delta t} + "
        r"\left[\frac{\partial}{\partial x}\left(\alpha\frac{Q^2}{A}\right)"
        r"\right]_j^{n+1/2} + \frac{A_{f,j}^{n+1/2}}{\rho}"
        r"\left[\frac{\partial P}{\partial x}\right]_j^{n+1/2} + "
        r"\kappa\frac{Q_j^{n+1/2}}{A_{f,j}^{n+1/2}}.$$",
        "",
        "Boundary pressure gradients use half-cell distances and PhysioBlocks "
        r"terminal fluxes use $Q_{\mathrm{node\,1}}=-Q_0$ and "
        r"$Q_{\mathrm{node\,2}}=Q_3$.",
        "",
        "The log-area Jacobian columns use the chain rule:",
        "",
        r"$$\frac{\partial R}{\partial g_i} = "
        r"\frac{\partial R}{\partial A_i}A_i.$$",
        "",
        "Prototype free parameters are `length` in $\\mathrm{m}$, "
        "`reference_area` in $\\mathrm{m^2}$, `wall_stiffness` in "
        "$\\mathrm{Pa\\,m^{-1}}$, `external_pressure` in $\\mathrm{Pa}$, "
        "`density` in $\\mathrm{kg\\,m^{-3}}$, `friction_coefficient` in "
        "$\\mathrm{m^2\\,s^{-1}}$, and dimensionless `momentum_correction`.",
        "",
        "The complete Task 010 equation notes, validation status, saved "
        "quantities, and limitations are maintained in "
        "`docs/one_d_numerics.md`.",
        "",
    ]


def coupled_openloop_section(spec: ModelSpec) -> list[str]:
    if spec.name != "coupled_0d_1d":
        return []
    return [
        "## Open-Loop 1-D Reference Specs",
        "",
        "Task 011 adds strict-JSON reference specs for three open-loop 1-D "
        "submodels:",
        "",
        "- `models/coupled_0d_1d/configs/submodel_aorta_1d_openloop.jsonc`",
        "- `models/coupled_0d_1d/configs/submodel_tcpc_1d_openloop.jsonc`",
        "- `models/coupled_0d_1d/configs/submodel_aorta_tcpc_1d_openloop.jsonc`",
        "",
        "These files are generated by "
        "`scripts/modeling/derive_1d_geometry.py`. They bind the tracked "
        "patient-specific geometry, measured inflows, Nektar reference domain "
        "files, paper/comparison reference tables, clinical comparison targets, "
        "and validation tolerances. They are not PhysioBlocks launcher configs "
        "and they do not promote a coupled closed-loop model.",
        "",
        "The aorta spec contains four source segments: ascending aorta, "
        "thoracic aorta, brachiocephalic, and left carotid. A normal LSA branch "
        "is not added because it is absent from the patient-specific geometry "
        "table.",
        "",
        "The TCPC spec contains five source segments: IVC, RPA, LPA I, LPA II, "
        "and SVC. The combined spec maps aorta domains 1-4 and TCPC domains "
        "5-9 in the tracked combined Nektar output.",
        "",
        "Validation is run with:",
        "",
        "```bash",
        "python3 scripts/calibration/validate_1d_submodels.py",
        "```",
        "",
        "The current report is "
        "`models/coupled_0d_1d/reference_outputs/openloop_1d_validation.json` "
        "and all three open-loop specs pass the current reference screen. The "
        "detailed Task 011 policy, inputs, tolerances, and limitations are "
        "maintained in `docs/openloop_1d_submodels.md`.",
        "",
    ]


def coupled_closedloop_section(spec: ModelSpec) -> list[str]:
    if spec.name != "coupled_0d_1d":
        return []
    return [
        "## Task 012 Closed-Loop Prototype",
        "",
        "Task 012 generates executable closed-loop configs with:",
        "",
        "```bash",
        "python3 scripts/modeling/build_coupled_configs.py",
        "python3 scripts/modeling/build_coupled_configs.py --check",
        "```",
        "",
        "The generator starts from the full 0-D scenario configs, removes the "
        "aortic and TCPC shortcut blocks, and inserts seven three-cell true "
        "1-D log-area vessel blocks, one six-cell tapered LPA block, one "
        "massless aortic total-pressure junction, one massless "
        "wall-pressure-blended dissipative TCPC total-pressure junction, "
        "and three downstream aortic residual "
        "interface loss blocks. The calibrated full 0-D LSA terminal branch is "
        "retained as a non-1-D aortic outlet because no patient-specific LSA "
        "1-D geometry is available.",
        "",
        "Aortic 1-D blocks:",
        "",
        "| Block | Nodes | Source segment |",
        "| --- | --- | --- |",
        "| `coupled_aao` | `aao -> coupled_aao_arch` | Ascending aorta |",
        "| `coupled_dao` | `coupled_dao_arch -> coupled_dao_out` | Thoracic aorta |",
        "| `coupled_bca` | `coupled_bca_arch -> coupled_bca_out` | Brachiocephalic |",
        "| `coupled_lcca` | `coupled_lcca_arch -> coupled_lcca_out` | Carotic left |",
        "| `coupled_aortic_arch_junction` | AAo/DAo/BCA/LCCA/LSA ports | total-pressure junction |",
        "",
        "TCPC 1-D blocks and junction:",
        "",
        "| Block | Nodes | Source segment |",
        "| --- | --- | --- |",
        "| `coupled_svc` | `svc -> coupled_svc_tcpc` | SVC |",
        "| `coupled_ivc` | `ivc -> coupled_ivc_tcpc` | IVC |",
        "| `coupled_rpa` | `coupled_rpa_tcpc -> rpa` | RPA |",
        "| `coupled_lpa` | `coupled_lpa_tcpc -> lpa` | LPA I + LPA II |",
        "| `coupled_tcpc_junction` | SVC/IVC/RPA/LPA branch ports | dissipative total-pressure junction |",
        "",
        "Residual aortic loss blocks preserve the full 0-D shortcut resistance "
        "not already represented by 1-D Poiseuille friction. For a retained "
        "path:",
        "",
        r"$$R_{\mathrm{loss}} = "
        r"\max(R_{\mathrm{full\,0D}} - R_{\mathrm{1D}}, 0).$$",
        "",
        "The TCPC junction enforces algebraic mass balance with effective "
        "branch total-pressure compatibility:",
        "",
        r"$$Q_{\mathrm{SVC}} + Q_{\mathrm{IVC}} "
        r"- Q_{\mathrm{RPA}} - Q_{\mathrm{LPA}} = 0,$$",
        "",
        r"$$H_k^\ast - H_{\mathrm{RPA}}^\ast = 0,\qquad "
        r"k \in \{\mathrm{SVC},\mathrm{IVC},\mathrm{LPA}\},$$",
        "",
        r"$$H_i^\ast = H_i + L_i,$$",
        "",
        r"$$H_i = wP_{\mathrm{wall},i} + (1-w)P_{\mathrm{node},i}"
        r" + \frac{1}{2}\rho\left(\frac{Q_i}{A_i}\right)^2,$$",
        "",
        r"$$L_i = \frac{1}{2}\rho K"
        r"\frac{q_{\mathrm{out},i}"
        r"\sqrt{q_{\mathrm{out},i}^2+\epsilon_Q^2}}{A_i^2}.$$",
        "",
        "The current generated TCPC settings are "
        "`wall_pressure_weight = 0.75`, `loss_coefficient = 2.0`, and "
        "`characteristic_scale = 0.0`. The aortic junction remains a no-loss "
        "total-pressure coupler.",
        "",
        "All generated coupled scenarios cap `time.step_size` at "
        "`0.00025 s` and `time.min_step` at `1.5625e-05 s`; the inherited "
        "full 0-D `0.002 s` step can make the first coupled nonlinear solve "
        "intractable.",
        "",
        "The current startup smoke run completes 0.025 s with no NaNs, no "
        "negative saved 1-D areas, near-zero aortic/TCPC junction mass "
        "residuals, passing TCPC balance, and bounded TCPC effective "
        "total-pressure spread around 0.36 mmHg. The smoke run remains a "
        "startup integration test rather than a physiological cycle "
        "validation. The tracked report is "
        "`models/coupled_0d_1d/reference_outputs/closed_loop_smoke_validation.json`.",
        "",
        "The 20 s baseline completes with no NaNs, no negative saved 1-D "
        "areas, passing TCPC, atrium, and ventricle balance, and cavity-volume "
        "periodicity of 0.000243. The tracked metrics are "
        "`models/coupled_0d_1d/reference_outputs/baseline_20s_metrics.json`. "
        "This establishes numerical viability, but Task 013 calibration and "
        "scenario validation are still in progress.",
        "",
    ]


def artifacts_section(spec: ModelSpec) -> list[str]:
    md_name = f"{spec.name}_technical_reference.md"
    pdf_name = f"{spec.name}_technical_reference.pdf"
    paths = [
        model_dir(spec) / "README.md",
        docs_dir(spec) / f"{spec.name}_schematic.svg",
        docs_dir(spec) / f"{spec.name}_schematic.png",
        docs_dir(spec) / "implementation_notes.md",
        docs_dir(spec) / md_name,
        docs_dir(spec) / pdf_name,
    ]
    if spec.name == "coupled_0d_1d":
        paths.insert(3, docs_dir(spec) / "physioblocks_feasibility.md")
        paths.insert(4, docs_dir(spec) / "one_d_numerics.md")
        paths.insert(5, docs_dir(spec) / "openloop_1d_submodels.md")
        paths.extend(
            [
                model_dir(spec) / "configs/fontan_coupled_0d_1d_smoke.jsonc",
                model_dir(spec) / "configs/fontan_coupled_0d_1d_baseline.jsonc",
                model_dir(spec) / "configs/fontan_coupled_0d_1d_vasodilation.jsonc",
                model_dir(spec) / "configs/fontan_coupled_0d_1d_fenestration.jsonc",
                model_dir(spec) / "configs/fontan_coupled_0d_1d_lpa_obstruction.jsonc",
                model_dir(spec) / "configs/submodel_aorta_1d_openloop.jsonc",
                model_dir(spec) / "configs/submodel_tcpc_1d_openloop.jsonc",
                model_dir(spec) / "configs/submodel_aorta_tcpc_1d_openloop.jsonc",
                model_dir(spec) / "calibration/one_d_openloop_geometry.json",
                model_dir(spec) / "reference_outputs/openloop_1d_validation.json",
                model_dir(spec) / "reference_outputs/smoke_metrics.json",
                model_dir(spec) / "reference_outputs/closed_loop_smoke_validation.json",
            ]
        )
    lines = ["## Documentation and Regeneration", ""]
    lines.append("Model-local documentation artifacts:")
    lines.append("")
    for path in paths:
        lines.append(f"- {code(rel(path))}")
    lines.extend(
        [
            "",
            "Regenerate the technical reference source and PDF with:",
            "",
            "```bash",
            f"python3 scripts/docs/build_model_reference_pdfs.py --model {spec.name}",
            "```",
            "",
        ]
    )
    return lines


def limitations_section(spec: ModelSpec) -> list[str]:
    lines = ["## Current Limitations", ""]
    for item in spec.limitations:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "The model parameters and standardized data are for computational "
            "development and calibration workflows. Simulation outputs must not "
            "be presented as clinically validated without separate validation "
            "and documentation.",
            "",
        ]
    )
    return lines


def technical_reference_markdown(spec: ModelSpec) -> str:
    cfg = load_json(spec.baseline_config) if spec.baseline_config is not None else None
    lines: list[str] = [
        "---",
        f"title: {spec.title}",
        "subtitle: Standardized model definition, equations, segments, and free parameters",
        "---",
        "",
        f"# {spec.title}",
        "",
        "This document is generated from repository sources by "
        f"{code('scripts/docs/build_model_reference_pdfs.py')}. Edit the model "
        "config, implementation notes, schematic, or this generator, then "
        "regenerate the markdown and PDF together.",
        "",
    ]
    lines.extend(topology_section(spec, cfg))
    lines.extend(equation_section())
    lines.extend(coupled_1d_prototype_section(spec))
    lines.extend(coupled_openloop_section(spec))
    lines.extend(coupled_closedloop_section(spec))
    lines.extend(quasi_chain_section(cfg))
    lines.extend(segment_inventory_section(cfg))
    lines.extend(free_parameter_section(cfg))
    lines.extend(artifacts_section(spec))
    lines.extend(limitations_section(spec))
    return "\n".join(lines).rstrip() + "\n"


def build_pdf(markdown_path: Path, pdf_path: Path) -> None:
    pandoc = shutil.which("pandoc")
    if pandoc is None:
        raise RuntimeError("pandoc is required to build model technical reference PDFs")
    if shutil.which("xelatex") is None:
        raise RuntimeError("xelatex is required to build model technical reference PDFs")

    command = [
        pandoc,
        markdown_path.name,
        "--standalone",
        "--toc",
        "--number-sections",
        "--pdf-engine=xelatex",
        "-V",
        "geometry:margin=0.65in",
        "-V",
        "fontsize=9pt",
        "-V",
        "colorlinks=true",
        "-o",
        pdf_path.name,
    ]
    subprocess.run(command, cwd=markdown_path.parent, check=True)


def write_reference(spec: ModelSpec, *, skip_pdf: bool) -> None:
    docs_dir(spec).mkdir(parents=True, exist_ok=True)
    markdown_path = docs_dir(spec) / f"{spec.name}_technical_reference.md"
    pdf_path = docs_dir(spec) / f"{spec.name}_technical_reference.pdf"
    markdown_path.write_text(technical_reference_markdown(spec), encoding="utf-8")
    if not skip_pdf:
        build_pdf(markdown_path, pdf_path)


def check_reference(spec: ModelSpec) -> list[str]:
    errors: list[str] = []
    markdown_path = docs_dir(spec) / f"{spec.name}_technical_reference.md"
    pdf_path = docs_dir(spec) / f"{spec.name}_technical_reference.pdf"
    expected = technical_reference_markdown(spec)
    if not markdown_path.exists():
        errors.append(f"missing {rel(markdown_path)}")
    elif markdown_path.read_text(encoding="utf-8") != expected:
        errors.append(f"stale {rel(markdown_path)}")
    if not pdf_path.exists():
        errors.append(f"missing {rel(pdf_path)}")
    elif not pdf_path.read_bytes().startswith(b"%PDF"):
        errors.append(f"not a PDF: {rel(pdf_path)}")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        choices=[*MODEL_SPECS, "all"],
        default="all",
        help="Model family to build or check.",
    )
    parser.add_argument(
        "--skip-pdf",
        action="store_true",
        help="Write markdown only. Intended for debugging.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check that markdown sources are current and PDFs exist.",
    )
    return parser.parse_args()


def selected_specs(model: str) -> list[ModelSpec]:
    if model == "all":
        return [MODEL_SPECS[name] for name in sorted(MODEL_SPECS)]
    return [MODEL_SPECS[model]]


def main() -> int:
    args = parse_args()
    specs = selected_specs(args.model)
    if args.check:
        errors: list[str] = []
        for spec in specs:
            errors.extend(check_reference(spec))
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        return 0

    for spec in specs:
        write_reference(spec, skip_pdf=args.skip_pdf)
        print(f"wrote {rel(docs_dir(spec) / f'{spec.name}_technical_reference.md')}")
        if not args.skip_pdf:
            print(f"wrote {rel(docs_dir(spec) / f'{spec.name}_technical_reference.pdf')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
