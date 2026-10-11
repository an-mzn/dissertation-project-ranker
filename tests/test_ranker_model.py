import random
import unittest
from types import SimpleNamespace

import numpy as np

from ranker_model import fit_preferences
from ranker_schedule import prioritise_next


def session(tags, ranks=None, comparisons=None, history=None, scores=None):
    count = len(tags)
    return SimpleNamespace(
        projects=[["Supervisor", f"Project {i}"] for i in range(count)],
        reference_ratings=[{"ranks": [rank], "tags": project_tags}
                           for rank, project_tags in zip(ranks or ["2.1"] * count, tags)],
        comparisons=comparisons or [(a, b) for a in range(1, count + 1)
                                    for b in range(a + 1, count + 1)],
        history=history or [], position=len(history or []), scores=scores or [0] * count,
    )


class ModelTests(unittest.TestCase):
    def test_tags_transfer_to_an_unseen_project(self):
        ranker = session([["Mobile"], ["Theory"], ["Mobile"]],
                         comparisons=[(1, 2)] * 12 + [(1, 3), (2, 3)],
                         history=[(i, 0) for i in range(12)], scores=[120, -120, 0])
        model = fit_preferences(ranker)
        self.assertGreater(model["score"][2], 50)
        self.assertGreater(model["tag_effects"]["Mobile"], 0)
        self.assertLess(model["tag_effects"]["Theory"], 0)

    def test_more_tags_do_not_stack_initial_bonuses(self):
        ranker = session([["Mobile"], ["Mobile", "Web", "UX"]], ranks=["1.1", "3.99"])
        np.testing.assert_allclose(fit_preferences(ranker)["score"], [65, 65])

    def test_both_is_a_tie_and_two_positive_endorsements(self):
        ranker = session([["A"], ["B"]], history=[(0, 2)], scores=[10, 10])
        model = fit_preferences(ranker)
        np.testing.assert_allclose(model["score"][0], model["score"][1])
        self.assertGreater(model["score"][0], 65)
        self.assertEqual(model["answer_count"], 1)

    def test_skip_supplies_no_model_evidence(self):
        fresh = session([["A"], ["B"]])
        skipped = session([["A"], ["B"]], history=[(0, None)])
        np.testing.assert_allclose(fit_preferences(fresh)["score"], fit_preferences(skipped)["score"])
        self.assertEqual(fit_preferences(skipped)["answer_count"], 0)

    def test_a_and_b_are_symmetric(self):
        left = session([["A"], ["B"]], history=[(0, 0)], scores=[10, -10])
        right = session([["A"], ["B"]], comparisons=[(2, 1)], history=[(0, 1)], scores=[10, -10])
        np.testing.assert_allclose(fit_preferences(left)["score"], fit_preferences(right)["score"])

    def test_undo_removes_model_evidence(self):
        ranker = session([["A"], ["B"]], history=[(0, 0)], scores=[10, -10])
        fit_preferences(ranker)
        ranker.history.clear()
        ranker.position = 0
        ranker.scores = [0, 0]
        np.testing.assert_allclose(fit_preferences(ranker)["score"], [65, 65])

    def test_scheduler_preserves_pairs_and_defers_exclusions(self):
        ranker = session([["A"], ["B"], ["C"]], ranks=["1.1", "4.1", "excluded"])
        original = set(ranker.comparisons)
        prioritise_next(ranker, random.Random(1))
        self.assertEqual(ranker.comparisons[0], (1, 2))
        self.assertEqual(set(ranker.comparisons), original)


if __name__ == "__main__":
    unittest.main()
