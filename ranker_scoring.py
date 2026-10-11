"""Exposure-adjusted preference scores with a modest draft-interest prior."""


PRIOR_STRENGTH = 4


def interest_group(rating):
    if "draft_prior" in rating:
        prior = rating["draft_prior"]
        return ("Draft-informed" if prior != 0.5 else "Neutral"), prior
    if rating["ranks"] == ["excluded"]:
        return "Excluded", 0.5
    if not rating["ranks"]:
        return "Neutral", 0.5
    section = min(int(rank.split(".")[0]) for rank in rating["ranks"])
    if section <= 3:
        return "High interest · sections 1–3", 0.65
    if section <= 6:
        return "Medium interest · sections 4–6", 0.5
    return "Lower interest · sections 7–10", 0.35


def observed_stats(ranker):
    answered = [0] * len(ranker.projects)
    recorded = {position: choice for position, choice in ranker.history}
    # Older sessions can have an initial block from before undo history existed.
    # Treat those legacy comparisons as answered; known skips never count.
    estimated = len(recorded) < ranker.position
    for position, pair in enumerate(ranker.comparisons[:ranker.position]):
        if position in recorded and recorded[position] is None:
            continue
        for index in pair:
            answered[index - 1] += 1
    stats = []
    for points, count, rating in zip(ranker.scores, answered, ranker.reference_ratings):
        group, prior = interest_group(rating)
        # +10 maps to one positive outcome; -10 maps to zero. Both contributes
        # a positive outcome to each project. Four virtual outcomes smooth small samples.
        positive = (points / 10 + count) / 2
        adjusted = 100 * (positive + PRIOR_STRENGTH * prior) / (count + PRIOR_STRENGTH)
        stats.append({"score": adjusted, "answered": count, "group": group,
                      "points": points, "estimated_counts": estimated})
    return stats


def preference_stats(ranker):
    from ranker_model import fit_preferences
    model = fit_preferences(ranker)
    stats = observed_stats(ranker)
    for index, stat in enumerate(stats):
        stat["observed_score"] = stat["score"]
        stat["score"] = float(model["score"][index])
        stat["answered"] = int(model["answered"][index])
        stat["uncertainty"] = float(model["covariance"][index, index] ** 0.5)
        stat["tags"] = ranker.reference_ratings[index].get("tags", [])
    return stats


def ranked_indices(ranker, stats=None):
    stats = stats if stats is not None else preference_stats(ranker)
    return sorted(range(len(ranker.projects)), key=lambda i: (
        -stats[i]["score"], -stats[i]["answered"], ranker.projects[i][1].strip().casefold()
    ))
