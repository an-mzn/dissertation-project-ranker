"""Atomic local checkpoints for project-ranking sessions."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


SESSION_PATH = Path("ranker-session.json")


def project_ids(projects):
    return [[row[0].strip(), row[1].strip()] for row in projects]


def validate(state, projects):
    if not isinstance(state, dict):
        raise ValueError("Saved session must be an object.")
    if state.get("version") != 1 or state.get("projects") != project_ids(projects):
        raise ValueError("Saved session belongs to a different project list.")
    count = len(projects)
    scores = state["scores"]
    pairs = state["comparisons"]
    position = state["position"]
    history = state["history"]
    if not all(isinstance(value, list) for value in (scores, pairs, history)):
        raise ValueError("Saved scores, comparisons, and history must be lists.")
    if (len(scores) != count or any(type(score) is not int or score % 10 for score in scores)
            or sum(scores) < 0 or sum(scores) % 20):
        raise ValueError("Invalid saved scores.")
    expected = {(a, b) for a in range(1, count + 1) for b in range(a + 1, count + 1)}
    if (any(not isinstance(pair, (list, tuple)) or len(pair) != 2 or any(type(i) is not int for i in pair) for pair in pairs)
            or len(pairs) != len(expected) or {tuple(pair) for pair in pairs} != expected):
        raise ValueError("Invalid saved comparison order.")
    if type(position) is not int or not 0 <= position <= len(pairs):
        raise ValueError("Invalid saved position.")
    if len(history) > position:
        raise ValueError("Invalid saved undo history.")
    for offset, entry in enumerate(history, position - len(history)):
        if (not isinstance(entry, (list, tuple)) or len(entry) != 2 or type(entry[0]) is not int or entry[0] != offset
                or (entry[1] is not None and (type(entry[1]) is not int or entry[1] not in (0, 1, 2)))):
            raise ValueError("Invalid saved undo history.")
    if type(state["stopped"]) is not bool:
        raise ValueError("Invalid saved pause state.")
    if type(state.get("adaptive_schedule", False)) is not bool:
        raise ValueError("Invalid saved adaptive schedule flag.")
    if type(state.get("answer_budget", 250)) is not int or state.get("answer_budget", 250) < 1:
        raise ValueError("Invalid saved answer budget.")
    if (type(state.get("stability_review_after", 0)) is not int
            or state.get("stability_review_after", 0) < 0):
        raise ValueError("Invalid saved stability review threshold.")
    return state


def load_session(path, projects):
    path = Path(path)
    backup = path.with_suffix(path.suffix + ".bak")
    if not path.exists() and not backup.exists():
        return None
    for candidate in (path, backup):
        try:
            return validate(json.loads(candidate.read_text(encoding="utf-8")), projects)
        except (OSError, ValueError, KeyError, TypeError):
            continue
    raise ValueError(
        f"Cannot restore {path} or its backup. The saved files were left untouched. "
        "Check the project list and save files before continuing."
    )


def atomic_write(path, payload):
    path = Path(path)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", delete=False) as f:
        temporary = Path(f.name)
        try:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def save_session(path, ranker):
    path = Path(path)
    state = {
        "version": 1,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "projects": project_ids(ranker.projects),
        "scores": list(ranker.scores),
        "comparisons": list(ranker.comparisons),
        "position": ranker.position,
        "history": list(ranker.history),
        "stopped": ranker.choose_a.disabled,
        "adaptive_schedule": getattr(ranker, "adaptive_schedule", False),
        "answer_budget": getattr(ranker, "answer_budget", 250),
        "stability_review_after": getattr(ranker, "stability_review_after", 0),
    }
    validate(state, ranker.projects)
    # Retain the preceding valid checkpoint as a recovery copy.
    if path.exists():
        previous = path.read_bytes()
        try:
            validate(json.loads(previous), ranker.projects)
        except (ValueError, KeyError, TypeError):
            pass
        else:
            atomic_write(path.with_suffix(path.suffix + ".bak"), previous)
    atomic_write(path, (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
