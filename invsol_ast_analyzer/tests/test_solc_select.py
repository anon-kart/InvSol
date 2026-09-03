import pytest

from invsol_ast.utils.solc_select import (
    constraint_bounds,
    parse_version,
    read_pragma,
    satisfies,
)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("0.8.19", (0, 8, 19)),
        ("v0.7.6", (0, 7, 6)),
        ("0.8", (0, 8, 0)),
        ("solc-0.8.23", (0, 8, 23)),
    ],
)
def test_parse_version(text, expected):
    assert parse_version(text) == expected


@pytest.mark.parametrize(
    "pragma,version,expected",
    [
        ("0.8.19", "0.8.19", True),
        ("0.8.19", "0.8.26", False),
        ("0.8.19", "0.8.18", False),
        ("^0.8.19", "0.8.19", True),
        ("^0.8.19", "0.8.26", True),
        ("^0.8.19", "0.8.18", False),
        ("^0.8.19", "0.9.0", False),
        ("^0.8.0", "0.8.26", True),
        ("^0.8.0", "0.7.6", False),
        ("^0.4.24", "0.4.26", True),
        ("^0.4.24", "0.5.0", False),
        ("~0.8.19", "0.8.26", True),
        ("~0.8.19", "0.9.0", False),
        (">=0.7.0 <0.9.0", "0.7.0", True),
        (">=0.7.0 <0.9.0", "0.8.26", True),
        (">=0.7.0 <0.9.0", "0.9.0", False),
        (">=0.7.0 <0.9.0", "0.6.12", False),
        (">=0.4.22 <0.9.0", "0.8.23", True),
        (">=0.4.22 <0.9.0", "0.4.21", False),
    ],
)
def test_satisfies(pragma, version, expected):
    assert satisfies(parse_version(version), pragma) is expected


def test_exact_pin_produces_equality_bound():
    assert constraint_bounds("0.8.19") == [("=", (0, 8, 19))]


def test_caret_expands_to_a_range():
    assert constraint_bounds("^0.8.19") == [(">=", (0, 8, 19)), ("<", (0, 9, 0))]


def test_empty_constraint_accepts_anything():
    assert satisfies((0, 8, 26), "") is True


def test_read_pragma(tmp_path):
    f = tmp_path / "C.sol"
    f.write_text("// SPDX-License-Identifier: MIT\npragma solidity 0.8.19;\ncontract C {}\n")
    assert read_pragma(str(f)) == "0.8.19"


def test_read_pragma_missing(tmp_path):
    f = tmp_path / "C.sol"
    f.write_text("contract C {}\n")
    assert read_pragma(str(f)) == ""
