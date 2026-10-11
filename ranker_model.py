"""Tag-aware Bayesian Bradley–Terry preferences with a Laplace approximation."""

import numpy as np


def sigmoid(value):
    value = np.clip(value, -35, 35)
    return 1 / (1 + np.exp(-value))


def fit_preferences(ranker):
    from ranker_scoring import interest_group

    signature = (
        tuple(ranker.scores),
        tuple((position, choice, tuple(ranker.comparisons[position]))
              for position, choice in ranker.history),
        tuple((tuple(r["ranks"]), tuple(r.get("tags", [])), r.get("draft_prior")) for r in ranker.reference_ratings),
        ranker.position,
    )
    if getattr(ranker, "_model_signature", None) == signature:
        return ranker._preference_model
    count = len(ranker.projects)
    tags = sorted({tag for r in ranker.reference_ratings for tag in r.get("tags", [])})
    tag_index = {tag: index for index, tag in enumerate(tags)}
    features = np.zeros((count, count + len(tags)))
    features[:, :count] = np.eye(count)
    mean = np.zeros(features.shape[1])
    precision = np.ones(features.shape[1])
    precision[count:] = 2.0
    for index, rating in enumerate(ranker.reference_ratings):
        _, prior = interest_group(rating)
        mean[index] = np.log(prior / (1 - prior))
        project_tags = rating.get("tags", [])
        # Normalisation prevents projects with more labels getting larger priors.
        for tag in project_tags:
            features[index, count + tag_index[tag]] = 1 / np.sqrt(len(project_tags))

    design, outcomes, weights = [], [], []
    answered = np.zeros(count, dtype=int)
    baseline_points = np.array(ranker.scores, dtype=float)
    recorded = {}
    for position, choice in ranker.history:
        recorded[position] = choice
        if choice is None:
            continue
        a, b = (index - 1 for index in ranker.comparisons[position])
        answered[[a, b]] += 1
        design.append(features[a] - features[b])
        outcomes.append(1.0 if choice == 0 else 0.0 if choice == 1 else 0.5)
        weights.append(1.0)
        if choice == 2:
            baseline_points[[a, b]] -= 10
            # A tie alone does not express that both are liked. Retain two modest
            # positive endorsements against a fixed neutral reference as well.
            for index in (a, b):
                design.append(features[index])
                outcomes.append(1.0)
                weights.append(0.5)
        else:
            winner, loser = (a, b) if choice == 0 else (b, a)
            baseline_points[winner] -= 10
            baseline_points[loser] += 10

    legacy_counts = np.zeros(count, dtype=int)
    for position, pair in enumerate(ranker.comparisons[:ranker.position]):
        if position not in recorded:
            for index in pair:
                legacy_counts[index - 1] += 1
    # Preserve old aggregate evidence if a session predates complete history;
    # opponent strength is unavailable for that initial block.
    for index, appearances in enumerate(legacy_counts):
        if appearances:
            design.append(features[index])
            outcomes.append(float(np.clip((baseline_points[index] / 10 / appearances + 1) / 2, 0, 1)))
            weights.append(float(appearances))
    answered += legacy_counts
    x = np.array(design).reshape((-1, features.shape[1]))
    y = np.array(outcomes)
    w = np.array(weights)
    theta = mean.copy()
    hessian = np.diag(precision)
    for _ in range(30):
        probability = sigmoid(x @ theta)
        gradient = precision * (theta - mean) + x.T @ (w * (probability - y))
        curvature = w * probability * (1 - probability)
        hessian = np.diag(precision) + (x.T * curvature) @ x
        step = np.linalg.solve(hessian, gradient)
        # Backtracking keeps Newton steps stable on strongly separated outcomes.
        def loss(candidate):
            logits = x @ candidate
            return 0.5 * np.sum(precision * (candidate - mean) ** 2) + np.sum(
                w * (np.logaddexp(0, logits) - y * logits)
            )
        scale = 1.0
        current_loss = loss(theta)
        while scale > 1 / 128 and loss(theta - scale * step) > current_loss:
            scale /= 2
        theta -= scale * step
        if np.max(np.abs(scale * step)) < 1e-7:
            break
    probability = sigmoid(x @ theta)
    hessian = np.diag(precision) + (x.T * (w * probability * (1 - probability))) @ x
    covariance = np.linalg.solve(hessian, np.eye(len(theta)))
    strength = features @ theta
    strength_covariance = features @ covariance @ features.T
    model = {
        "strength": strength,
        "covariance": strength_covariance,
        "score": 100 * sigmoid(strength),
        "answered": answered,
        "tags": tags,
        "tag_effects": dict(zip(tags, theta[count:].tolist())),
        "answer_count": sum(choice is not None for _, choice in ranker.history)
                        + ranker.position - len(recorded),
        "legacy": bool(legacy_counts.any()),
    }
    ranker._model_signature = signature
    ranker._preference_model = model
    return model


def shortlist_status(ranker, model=None):
    model = model if model is not None else fit_preferences(ranker)
    if "shortlist_status" in model:
        return model["shortlist_status"]
    active = np.array([i for i, r in enumerate(ranker.reference_ratings) if r["ranks"] != ["excluded"]])
    # Deterministic posterior samples avoid flickering confidence on display refresh.
    rng = np.random.default_rng(2026)
    covariance = model["covariance"][np.ix_(active, active)]
    samples = rng.multivariate_normal(model["strength"][active], covariance, size=256)
    top_count = min(10, len(active))
    sampled_top = np.argsort(samples, axis=1)[:, -top_count:]
    membership = np.bincount(sampled_top.ravel(), minlength=len(active)) / len(samples)
    current_top = np.argsort(model["strength"][active])[-top_count:]
    stability = float(membership[current_top].mean())
    covered = float(np.mean(model["answered"][active] > 0))
    stable = model["answer_count"] >= 120 and covered >= 0.9 and stability >= 0.9
    result = {"stability": stability, "coverage": covered, "stable": stable,
              "membership": dict(zip(active.tolist(), membership.tolist()))}
    model["shortlist_status"] = result
    return result
