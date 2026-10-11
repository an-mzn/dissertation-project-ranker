"""Prioritise remaining comparisons without changing scores or answered pairs."""

import random


EXCLUDED_DELAY = 1000


def prioritise_next(ranker, rng=None):
    """Choose an informative remaining pair, reserving exploration opportunities."""
    from ranker_model import fit_preferences, shortlist_status, sigmoid
    import numpy as np

    if ranker.position >= len(ranker.comparisons):
        return
    rng = rng or random
    model = fit_preferences(ranker)
    shortlist = shortlist_status(ranker, model)
    shown = np.zeros(len(ranker.projects), dtype=int)
    for pair in ranker.comparisons[:ranker.position]:
        for index in pair:
            shown[index - 1] += 1
    excluded = [rating["ranks"] == ["excluded"] for rating in ranker.reference_ratings]
    candidates = [offset for offset in range(ranker.position, len(ranker.comparisons))
                  if ranker.position >= EXCLUDED_DELAY or not any(
                      excluded[index - 1] for index in ranker.comparisons[offset])]
    if not candidates:
        candidates = list(range(ranker.position, len(ranker.comparisons)))
    pairs = np.array([ranker.comparisons[offset] for offset in candidates]) - 1
    a, b = pairs[:, 0], pairs[:, 1]
    if rng.random() < 0.25:
        # Regular exploration prevents an early prediction from excluding a good project.
        weights = 1 / ((1 + shown[a]) * (1 + shown[b]))
    else:
        covariance = model["covariance"]
        variance = np.maximum(0, covariance[a, a] + covariance[b, b] - 2 * covariance[a, b])
        probability = sigmoid(model["strength"][a] - model["strength"][b])
        information = 4 * probability * (1 - probability) * variance / (1 + variance)
        order = np.argsort(model["strength"])[::-1]
        eligible = [i for i in order if not excluded[i]]
        cutoff = model["strength"][eligible[min(19, len(eligible) - 1)]]
        deviations = np.sqrt(np.maximum(np.diag(covariance), 1e-8))
        contender = sigmoid((model["strength"] - cutoff) / deviations)
        membership = np.array([shortlist["membership"].get(i, 0)
                               for i in range(len(ranker.projects))])
        uncertain_membership = 4 * membership * (1 - membership)
        relevance = 0.05 + np.maximum(contender[a], contender[b]) + np.maximum(
            uncertain_membership[a], uncertain_membership[b])
        weights = (0.02 + information) * relevance / np.sqrt(1 + shown[a] + shown[b])
    # Keep exclusions rare even after their delay expires.
    penalties = np.array([0.1 if excluded[i] else 1 for i in range(len(excluded))])
    weights *= penalties[a] * penalties[b]
    selected = rng.choices(candidates, weights=weights.tolist(), k=1)[0]
    ranker.comparisons[ranker.position], ranker.comparisons[selected] = (
        ranker.comparisons[selected], ranker.comparisons[ranker.position]
    )
