from testcrafter.instrument.loop_probe import _watched_for

MAPPING_ACCUMULATOR = {
    "body_summary": {
        "carried_vars": ["rewardOf", "total"],
        "carried_types": {"rewardOf": "uint256", "total": "uint256"},
        "declared_vars": [],
        "indices": ["i"],
        "mapping_update_facts": [{"var": "rewardOf", "container": "mapping"}],
        "array_update_facts": [],
    }
}

ARRAY_ACCUMULATOR = {
    "body_summary": {
        "carried_vars": ["slots", "total"],
        "carried_types": {"slots": "uint256", "total": "uint256"},
        "declared_vars": [],
        "indices": ["i"],
        "mapping_update_facts": [],
        "array_update_facts": [{"var": "slots", "container": "array"}],
    }
}


def test_a_mapping_accumulator_is_not_watched_by_name():
    # rewardOf[stakers[i]] += x records the value type uint256, but rewardOf is
    # the whole mapping and uint256(rewardOf) does not compile.
    watched = dict(_watched_for(MAPPING_ACCUMULATOR, exclude_declared=True))
    assert "rewardOf" not in watched
    assert watched["total"] == "uint256"


def test_an_array_accumulator_is_not_watched_by_name():
    watched = dict(_watched_for(ARRAY_ACCUMULATOR, exclude_declared=True))
    assert "slots" not in watched
    assert watched["total"] == "uint256"


def test_a_plain_scalar_is_still_watched():
    plain = {
        "body_summary": {
            "carried_vars": ["sum"],
            "carried_types": {"sum": "uint256"},
            "declared_vars": [],
            "indices": [],
        }
    }
    assert _watched_for(plain, exclude_declared=True) == [("sum", "uint256")]
