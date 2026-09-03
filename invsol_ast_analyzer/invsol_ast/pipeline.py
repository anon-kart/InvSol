from typing import Any, Dict, Optional

# AST stage
from .ast import (
    parser,
    normalizer,
    extractor_functions,
    extractor_loops,
    extractor_require,
    extractor_state,
    access_control,
    extractor_effects,   # NEW
)

# IR stage
from .ir import build_ir, json_exporter

# Validators
from .validators import schema_validator, consistency_checks

# Utils
from .utils import logging as log
from .utils import solc_wrapper
from .utils.errors import ValidationError

from .config import IR_VERSION


def _get_ast(path: str, solc_path: Optional[str]) -> Dict[str, Any]:
    """
    Prefer the shared solc wrapper when an explicit solc_path is given;
    otherwise fall back to parser.parse_solidity_to_ast (dev-friendly).
    """
    if solc_path:
        ast = solc_wrapper.get_ast_best_effort(path, solc_path=solc_path)
        return {"source": path, "ast": ast}
    return parser.parse_solidity_to_ast(path)


def run_pipeline(
    path: str,
    out: str,
    *,
    solc_path: Optional[str] = None,
    validate: bool = True,
    strict: bool = False,
    dump_ast: Optional[str] = None,  # save normalized AST JSON if provided
) -> Dict[str, Any]:
    """parse -> normalize -> extract -> build -> (validate) -> export"""

    # 1) Parse
    with log.timed("parse"):
        ast_bundle = _get_ast(path, solc_path)

    # 2) Normalize
    with log.timed("normalize"):
        norm = normalizer.normalize_ast(ast_bundle)

    # Optional: dump normalized analyzer JSON
    if dump_ast:
        json_exporter.write_json(norm, dump_ast)
        log.info(f"Wrote normalized AST (analyzer JSON) to {dump_ast}")

    contracts = norm.get("contracts") or []
    if not contracts:
        raise ValidationError(
            f"No contract was found in {path}. solc returned an AST with no "
            "ContractDefinition node, so every later stage would produce nothing. "
            "Check `solc --version` against the pragma in the file."
        )

    # Build a state index for downstream passes
    state_index = extractor_effects.build_state_index_from_norm(norm)

    # 3) Extract
    with log.timed("extract: functions"):
        funcs = extractor_functions.extract_functions(norm)
    if not funcs:
        log.warning(
            f"{len(contracts)} contract(s) parsed but no function was extracted from "
            f"{path}. Downstream postcondition inference will be empty."
        )

    with log.timed("extract: loops"):
        loops = extractor_loops.extract_loops(norm, state_index=state_index)  # pass index

    with log.timed("extract: requires"):
        reqs = extractor_require.extract_requires(norm)

    with log.timed("extract: modifier requires"):
        # NOTE: this dict must support both plain and contract-qualified keys:
        #   { "onlyOwner": [...], "AssetTransfer.onlyOwner": [...] }
        modifier_requires = extractor_require.extract_modifier_requires(norm)

    # Attach modifier-level requires to functions (so they show up in function.requires)
    # We look up both qualified and plain keys.
    reqs_aug = list(reqs)
    for f in funcs:
        c = f.get("contract") or ""
        fname = f.get("name") or ""
        for mod in f.get("modifiers") or []:
            qkey = f"{c}.{mod}" if c else mod
            conds = modifier_requires.get(qkey) or modifier_requires.get(mod) or []
            for cond in conds:
                reqs_aug.append(
                    {"contract": c, "function": fname, "condition": cond, "node_id": None}
                )

    # De-dup requires per function
    dedup: Dict[tuple, set] = {}
    for r in reqs_aug:
        key = (r["contract"], r["function"])
        dedup.setdefault(key, set()).add(r["condition"])
    reqs_aug = [
        {"contract": c, "function": f, "condition": cond, "node_id": None}
        for (c, f), conds in dedup.items()
        for cond in sorted(conds)
    ]

    with log.timed("extract: state"):
        state = extractor_state.extract_state(norm)

    with log.timed("extract: access control"):
        acl = access_control.resolve_access_control(norm)

    with log.timed("extract: function effects"):
        fn_effects = extractor_effects.extract_function_effects(norm, state_index=state_index)

    # 4) Build IR
    with log.timed("build IR"):
        try:
            # Works whether solc_path is None or a path; wrapper uses "solc" on PATH if None
            solidity_version = solc_wrapper.get_solc_version(solc_path)
        except Exception:
            solidity_version = None


        ir = build_ir.build(
            functions=funcs,
            loops=loops,
            requires=reqs_aug,
            state=state,
            acl=acl,
            solidity_version=solidity_version,
            version=IR_VERSION,
            function_effects=fn_effects,        # effects map keyed by (contract, function)
            modifier_requires=modifier_requires # pass through for access_dependencies merge
        )

    # 5) Validate
    if validate:
        with log.timed("validate: schema"):
            schema_errors = schema_validator.validate(ir)
        if schema_errors:
            msg = "IR schema validation issues:\n- " + "\n- ".join(schema_errors)
            if strict:
                raise ValidationError(msg)
            else:
                log.warning(msg)

        with log.timed("validate: consistency"):
            problems = consistency_checks.check(ir, strict=False)
        if problems:
            msg = "IR consistency issues:\n- " + "\n- ".join(problems)
            if strict:
                raise ValidationError(msg)
            else:
                log.warning(msg)

    # 6) Export
    with log.timed("export JSON"):
        json_exporter.write_json(ir, out)
        log.info(f"Wrote IR to {out}")

    return ir


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="Parse one Solidity file and write the InvSol IR."
    )
    ap.add_argument("path")
    ap.add_argument("-o", "--out", default="ir.json")
    ap.add_argument("--solc-path", default=None)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--no-validate", action="store_true")
    parsed = ap.parse_args()

    run_pipeline(
        path=parsed.path,
        out=parsed.out,
        solc_path=parsed.solc_path,
        validate=not parsed.no_validate,
        strict=parsed.strict,
    )
