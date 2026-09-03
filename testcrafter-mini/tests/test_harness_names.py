import re

from testcrafter.synthesis.loop_harness import _array_setup, _call_arguments

BATCH_SEND = {
    "name": "batchSend",
    "params": [
        {"name": "to", "type": "address[]"},
        {"name": "amounts", "type": "uint256[]"},
    ],
}

AIRDROP = {
    "name": "airdropEqual",
    "params": [
        {"name": "to", "type": "address[]"},
        {"name": "amount", "type": "uint256"},
    ],
}


def declared_names(lines):
    out = []
    for line in lines:
        found = re.search(r"memory (\S+) = new ", line)
        if found:
            out.append(found.group(1))
    return out


def test_the_same_parameter_at_two_call_sites_gets_two_names():
    seed, _ = _call_arguments(BATCH_SEND, None, "    ", "seed0")
    call, _ = _call_arguments(BATCH_SEND, None, "    ", "call")

    names = declared_names(seed) + declared_names(call)
    assert len(names) == len(set(names)), names


def test_two_producers_sharing_a_parameter_name_do_not_collide():
    first, _ = _call_arguments(BATCH_SEND, None, "    ", "seed0")
    second, _ = _call_arguments(AIRDROP, None, "    ", "seed1")

    names = declared_names(first) + declared_names(second)
    assert len(names) == len(set(names)), names


def test_the_tag_appears_in_the_variable_name():
    lines, var = _array_setup("to", "address[]", 0, "    ", "seed0")
    assert var == "_seed0_to_0"
    assert any(var in line for line in lines)
