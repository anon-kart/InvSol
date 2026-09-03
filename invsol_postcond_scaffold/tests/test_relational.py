from invsol_postcond.relational import (
    LoopObservation,
    derive_for_loop,
    observations_from_summary,
    relations_from_facts,
    relations_from_traces,
)


def summary(loop_id, samples):
    return {"loops": [{"loop_id": loop_id, "samples": samples}]}


def run(entry, iterations, exit_values, trips):
    return {
        "entry": entry,
        "iterations": [{"index": i + 1, "values": v} for i, v in enumerate(iterations)],
        "exit": exit_values,
        "trip_count": trips,
    }


def exprs(relations, scope=None):
    return {r.expr for r in relations if scope is None or r.scope == scope}


ARRAY_SUM_LOOP = {
    "loop_id": "S.total#loop0",
    "bounds": {"index": "i", "lower": "0", "upper": "values.length"},
    "body_summary": {
        "accumulator_facts": [
            {
                "var": "acc",
                "op": "+=",
                "kind": "sum",
                "source": {"expr": "values[i]", "base": "values", "container": "array"},
            }
        ]
    },
}

COUNTER_LOOP = {
    "loop_id": "C.count#loop0",
    "bounds": {"index": "i", "lower": "0", "upper": "n"},
    "body_summary": {
        "accumulator_facts": [
            {"var": "c", "op": "+=", "kind": "count", "source": {"expr": "1", "base": ""}}
        ]
    },
}


class TestFactRelations:
    def test_array_accumulator_gives_a_total_on_exit(self):
        assert "acc == sum(values)" in exprs(relations_from_facts(ARRAY_SUM_LOOP), "post")

    def test_array_accumulator_gives_a_partial_sum_invariant(self):
        assert "acc <= sum(values)" in exprs(relations_from_facts(ARRAY_SUM_LOOP), "loop")

    def test_counter_is_bounded_by_the_loop_upper_bound(self):
        assert "c <= n" in exprs(relations_from_facts(COUNTER_LOOP), "loop")

    def test_counter_is_non_negative(self):
        assert "c >= 0" in exprs(relations_from_facts(COUNTER_LOOP))

    def test_mapping_update_gives_a_non_negative_total(self):
        loop = {
            "loop_id": "M.f#loop0",
            "body_summary": {"mapping_update_facts": [{"var": "balances"}]},
        }
        assert "sum(balances) >= 0" in exprs(relations_from_facts(loop))

    def test_loop_without_accumulators_yields_nothing(self):
        assert relations_from_facts({"loop_id": "x", "body_summary": {}}) == []


class TestTraceRelations:
    def test_cap_is_taken_from_entry_and_exit_not_just_iterations(self):
        obs = observations_from_summary(
            summary(
                "P#loop0",
                [
                    run({"s": "0"}, [{"s": "0"}, {"s": "40"}, {"s": "70"}], {"s": "100"}, 3),
                    run({"s": "0"}, [{"s": "0"}, {"s": "55"}], {"s": "100"}, 2),
                ],
            )
        )["P#loop0"]
        assert "s <= 100" in exprs(relations_from_traces(obs))

    def test_unremarkable_maximum_produces_no_cap(self):
        obs = observations_from_summary(
            summary("P#loop0", [run({"s": "0"}, [{"s": "7"}, {"s": "13"}], {"s": "37"}, 2)])
        )["P#loop0"]
        assert not any(e.startswith("s <=") for e in exprs(relations_from_traces(obs)))

    def test_monotone_variable_is_reported(self):
        obs = observations_from_summary(
            summary("P#loop0", [run({}, [{"t": "0"}, {"t": "3"}, {"t": "9"}], {}, 3)])
        )["P#loop0"]
        assert "t >= old(t)" in exprs(relations_from_traces(obs))

    def test_decreasing_variable_is_not_called_monotone(self):
        obs = observations_from_summary(
            summary("P#loop0", [run({}, [{"t": "9"}, {"t": "3"}], {}, 2)])
        )["P#loop0"]
        assert "t >= old(t)" not in exprs(relations_from_traces(obs))

    def test_unchanged_variable_is_reported_as_constant(self):
        obs = observations_from_summary(
            summary("P#loop0", [run({}, [{"k": "5"}, {"k": "5"}, {"k": "5"}], {}, 3)])
        )["P#loop0"]
        assert "k == old(k)" in exprs(relations_from_traces(obs))

    def test_index_tracking_counter_is_detected(self):
        obs = observations_from_summary(
            summary("P#loop0", [run({}, [{"i": "0"}, {"i": "1"}, {"i": "2"}], {}, 3)])
        )["P#loop0"]
        assert "i == iterations - 1" in exprs(relations_from_traces(obs))

    def test_negative_values_suppress_the_non_negative_claim(self):
        obs = observations_from_summary(
            summary("P#loop0", [run({}, [{"d": "-3"}, {"d": "2"}], {}, 2)])
        )["P#loop0"]
        assert "d >= 0" not in exprs(relations_from_traces(obs))

    def test_exit_never_below_entry_is_a_postcondition(self):
        obs = observations_from_summary(
            summary("P#loop0", [run({"s": "2"}, [{"s": "2"}], {"s": "9"}, 1)])
        )["P#loop0"]
        assert "s >= entry(s)" in exprs(relations_from_traces(obs), "post")

    def test_no_runs_gives_no_relations(self):
        assert relations_from_traces(LoopObservation(loop_id="x")) == []


class TestMotivatingExample:
    def test_payment_splitter_yields_the_cumulative_share_invariant(self):
        obs = observations_from_summary(
            summary(
                "P.distribute#loop0",
                [
                    run({"sumShares": "0"}, [{"sumShares": "0"}, {"sumShares": "40"}], {"sumShares": "100"}, 2),
                    run({"sumShares": "0"}, [{"sumShares": "0"}, {"sumShares": "55"}], {"sumShares": "100"}, 2),
                ],
            )
        )["P.distribute#loop0"]
        loop = {
            "loop_id": "P.distribute#loop0",
            "bounds": {"index": "i", "lower": "0", "upper": "payees.length"},
            "body_summary": {
                "accumulator_facts": [
                    {
                        "var": "sumShares",
                        "op": "+=",
                        "kind": "sum",
                        "source": {
                            "expr": "shares[payees[i]]",
                            "base": "shares",
                            "container": "mapping",
                        },
                    }
                ]
            },
        }
        found = exprs(derive_for_loop(loop, obs), "loop")
        assert "sumShares <= 100" in found
        assert "sumShares <= sum(shares)" in found


from invsol_postcond.relational import derive_for_contract


class TestCapPrecision:
    @staticmethod
    def _obs(samples, loop_id="L#loop0"):
        return observations_from_summary(summary(loop_id, samples))[loop_id]

    def test_index_variable_never_gets_a_numeric_cap(self):
        loop = {"loop_id": "L#loop0", "body_summary": {"indices": ["i"], "accumulator_facts": []}}
        obs = self._obs(
            [run({}, [{"i": "0"}, {"i": "10"}], {}, 2), run({}, [{"i": "0"}, {"i": "10"}], {}, 2)]
        )
        found = exprs(derive_for_loop(loop, obs))
        assert not any(e.startswith("i <=") for e in found)

    def test_accumulator_cap_survives_when_seen_repeatedly(self):
        loop = {
            "loop_id": "L#loop0",
            "body_summary": {
                "indices": ["i"],
                "accumulator_facts": [
                    {
                        "var": "s",
                        "op": "+=",
                        "kind": "sum",
                        "source": {"expr": "shares[k]", "base": "shares", "container": "mapping"},
                    }
                ],
            },
        }
        obs = self._obs(
            [
                run({"s": "0"}, [{"s": "0"}, {"s": "40"}], {"s": "100"}, 2),
                run({"s": "0"}, [{"s": "0"}, {"s": "60"}], {"s": "100"}, 2),
            ]
        )
        assert "s <= 100" in exprs(derive_for_loop(loop, obs))

    def test_peak_seen_in_a_single_run_is_rejected(self):
        loop = {"loop_id": "L#loop0", "body_summary": {"indices": [], "accumulator_facts": []}}
        obs = self._obs(
            [
                run({"s": "0"}, [{"s": "0"}], {"s": "100"}, 1),
                run({"s": "0"}, [{"s": "0"}], {"s": "40"}, 1),
            ]
        )
        assert "s <= 100" not in exprs(derive_for_loop(loop, obs))

    def test_one_is_no_longer_treated_as_a_meaningful_bound(self):
        loop = {"loop_id": "L#loop0", "body_summary": {"indices": [], "accumulator_facts": []}}
        obs = self._obs([run({}, [{"f": "0"}, {"f": "1"}], {}, 2), run({}, [{"f": "1"}], {}, 1)])
        assert "f <= 1" not in exprs(derive_for_loop(loop, obs))

    def test_trip_cap_needs_more_than_one_observation(self):
        loop = {"loop_id": "L#loop0", "body_summary": {"indices": [], "accumulator_facts": []}}
        obs = self._obs([run({}, [{"x": "1"}], {}, 10), run({}, [{"x": "1"}], {}, 3)])
        assert "iterations <= 10" not in exprs(derive_for_loop(loop, obs))


class TestFunctionLevelMerge:
    def test_two_loops_sharing_an_index_do_not_duplicate_relations(self):
        ir = {
            "contract": {
                "functions": [
                    {
                        "name": "bubble",
                        "loops": [
                            {"loop_id": "B#loop0", "body_summary": {"indices": ["i"], "accumulator_facts": []}},
                            {"loop_id": "B#loop1", "body_summary": {"indices": ["i"], "accumulator_facts": []}},
                        ],
                    }
                ]
            }
        }
        obs = observations_from_summary(
            {
                "loops": [
                    {"loop_id": "B#loop0", "samples": [run({}, [{"i": "0"}, {"i": "1"}], {}, 2)]},
                    {"loop_id": "B#loop1", "samples": [run({}, [{"i": "0"}, {"i": "1"}], {}, 2)]},
                ]
            }
        )
        found = [r.expr for r in derive_for_contract(ir, obs)["bubble"]]
        assert len(found) == len(set(found))

    def test_merge_keeps_the_better_supported_relation(self):
        ir = {
            "contract": {
                "functions": [
                    {
                        "name": "f",
                        "loops": [
                            {"loop_id": "F#loop0", "body_summary": {"indices": [], "accumulator_facts": []}},
                            {"loop_id": "F#loop1", "body_summary": {"indices": [], "accumulator_facts": []}},
                        ],
                    }
                ]
            }
        }
        obs = observations_from_summary(
            {
                "loops": [
                    {"loop_id": "F#loop0", "samples": [run({}, [{"t": "0"}, {"t": "1"}], {}, 2)]},
                    {
                        "loop_id": "F#loop1",
                        "samples": [
                            run({}, [{"t": "0"}, {"t": "1"}], {}, 2),
                            run({}, [{"t": "0"}, {"t": "2"}], {}, 2),
                        ],
                    },
                ]
            }
        )
        by_expr = {r.expr: r for r in derive_for_contract(ir, obs)["f"]}
        assert by_expr["t >= 0"].support == 2


class TestCounterEvidence:
    @staticmethod
    def _obs(samples):
        return observations_from_summary(summary("L#loop0", samples))["L#loop0"]

    def test_single_iteration_at_zero_is_not_a_counter(self):
        obs = self._obs(
            [
                run({"s": "0"}, [{"s": "0"}], {"s": "30"}, 1),
                run({"s": "0"}, [{"s": "0"}], {"s": "30"}, 1),
            ]
        )
        assert "s == iterations - 1" not in exprs(relations_from_traces(obs))

    def test_genuine_counter_is_still_detected(self):
        obs = self._obs([run({}, [{"c": "0"}, {"c": "1"}, {"c": "2"}, {"c": "3"}], {}, 4)])
        assert "c == iterations - 1" in exprs(relations_from_traces(obs))

    def test_constant_variable_is_not_mistaken_for_a_counter(self):
        obs = self._obs([run({}, [{"k": "0"}, {"k": "0"}, {"k": "0"}, {"k": "0"}], {}, 4)])
        found = exprs(relations_from_traces(obs))
        assert "k == iterations - 1" not in found
        assert "k == old(k)" in found

    def test_two_steps_are_not_enough_evidence(self):
        obs = self._obs([run({}, [{"c": "0"}, {"c": "1"}], {}, 2)])
        assert "c == iterations - 1" not in exprs(relations_from_traces(obs))


class TestCounterReset:
    LOOP = {
        "loop_id": "S#loop1",
        "bounds": {"index": "c", "lower": "0", "upper": "row.length"},
        "body_summary": {
            "indices": ["c"],
            "accumulator_facts": [
                {"var": "touched", "op": "+=", "kind": "count", "source": {"expr": "1", "base": ""}}
            ],
        },
    }

    @staticmethod
    def _obs(samples):
        return observations_from_summary(summary("S#loop1", samples))["S#loop1"]

    def test_counter_carried_between_entries_loses_its_bound(self):
        obs = self._obs(
            [
                run({"touched": "0"}, [{"touched": "0"}, {"touched": "1"}], {"touched": "3"}, 2),
                run({"touched": "3"}, [{"touched": "3"}, {"touched": "4"}], {"touched": "6"}, 2),
            ]
        )
        assert "touched <= row.length" not in exprs(derive_for_loop(self.LOOP, obs))

    def test_counter_reset_on_each_entry_keeps_its_bound(self):
        obs = self._obs(
            [
                run({"touched": "0"}, [{"touched": "0"}, {"touched": "1"}], {"touched": "2"}, 2),
                run({"touched": "0"}, [{"touched": "0"}, {"touched": "1"}], {"touched": "2"}, 2),
            ]
        )
        assert "touched <= row.length" in exprs(derive_for_loop(self.LOOP, obs))

    def test_other_relations_survive_the_filter(self):
        obs = self._obs(
            [
                run({"touched": "0"}, [{"touched": "0"}], {"touched": "3"}, 1),
                run({"touched": "3"}, [{"touched": "3"}], {"touched": "6"}, 1),
            ]
        )
        assert "touched >= 0" in exprs(derive_for_loop(self.LOOP, obs))
