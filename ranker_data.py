"""Load student CSVs into the ranker's existing project and metadata layouts."""

import csv
import re
import unicodedata
from pathlib import Path

FIELDS = {"title", "supervisor", "description", "tags", "summary", "tools",
          "difficulty", "ai_assistance", "readable_description", "draft_rank", "topics"}


def project_key(supervisor, title):
    def normalize(value):
        return " ".join(unicodedata.normalize("NFKC", value).strip().rstrip(".").casefold().split())
    return normalize(supervisor), normalize(title)


def load_projects(path, columns, *, has_header=True, delimiter=",", use_draft_prior=False):
    """Map header names or zero-based positions; return (projects, ratings).

    Only title is required. Tags are semicolon-separated; absent reference
    rankings intentionally have neutral priors.
    """
    if not isinstance(columns, dict) or columns.get("title") is None:
        raise ValueError("Map a title column before loading projects.")
    unknown = set(columns) - FIELDS
    if unknown:
        raise ValueError(f"Unknown column mappings: {', '.join(sorted(unknown))}")
    if not isinstance(delimiter, str) or len(delimiter) != 1:
        raise ValueError("CSV delimiter must be a single character.")
    projects, ratings, seen = [], [], set()
    draft_ranks = set()
    with Path(path).open(encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source, delimiter=delimiter)
        header = next(reader, None) if has_header else None
        indices = {}
        for field, column in columns.items():
            if column is None:
                continue
            if isinstance(column, str):
                if not has_header:
                    raise ValueError(f"Mapping {field!r} by name requires a header.")
                if header is None or header.count(column) != 1:
                    raise ValueError(f"Column header {column!r} must exist exactly once.")
                indices[field] = header.index(column)
            elif type(column) is int and column >= 0:
                if header is not None and column >= len(header):
                    raise ValueError(f"Column index {column} for {field!r} is outside the header.")
                indices[field] = column
            else:
                raise ValueError(f"Mapping {field!r} must be a header name or nonnegative integer.")
        for row in reader:
            if not row or not any(value.strip() for value in row):
                continue
            line = reader.line_num
            values = {}
            for field, index in indices.items():
                if index >= len(row):
                    raise ValueError(f"CSV row ending at line {line}: missing column {index} for {field}.")
                values[field] = row[index].strip()
            title = values.get("title", "")
            supervisor = values.get("supervisor", "")
            if not title:
                raise ValueError(f"CSV row ending at line {line}: title is required.")
            identity = project_key(supervisor, title)
            if identity in seen:
                raise ValueError(f"CSV row ending at line {line}: duplicate supervisor/title identity for {title!r}.")
            seen.add(identity)
            rating = {"ranks": [], "tags": list(dict.fromkeys(
                tag.strip() for tag in values.get("tags", "").split(";") if tag.strip())),
                "summary": values.get("summary", ""), "potential_stack": values.get("tools", ""),
                "difficulty": None, "ai_assistance": None,
                "readable_description": values.get("readable_description", ""),
                "sections": list(dict.fromkeys(topic.strip() for topic in
                    values.get("topics", "").split(";") if topic.strip())),
                "draft_rank": None, "draft_prior": 0.5}
            draft = values.get("draft_rank", "")
            if draft:
                if not re.fullmatch(r"[0-9]+", draft) or int(draft) < 1:
                    raise ValueError(f"CSV row ending at line {line}: draft_rank must be a positive integer.")
                rank = int(draft)
                if rank in draft_ranks:
                    raise ValueError(f"CSV row ending at line {line}: duplicate draft_rank {rank}.")
                draft_ranks.add(rank)
                rating["draft_rank"] = rank
            for field in ("difficulty", "ai_assistance"):
                value = values.get(field, "")
                if value:
                    try:
                        number = float(value)
                    except ValueError:
                        number = float("nan")
                    if not 1 <= number <= 10:
                        raise ValueError(f"CSV row ending at line {line}: {field} must be a number from 1 to 10.")
                    rating[field] = int(number) if number.is_integer() else number
            projects.append([supervisor, title, values.get("description", "")])
            ratings.append(rating)
    if len(projects) < 2:
        raise ValueError("Provide at least two projects to compare.")
    if use_draft_prior and len(draft_ranks) > 1:
        ordered = {rank: index for index, rank in enumerate(sorted(draft_ranks))}
        for rating in ratings:
            rank = rating["draft_rank"]
            if rank is not None:
                rating["draft_prior"] = 0.65 - 0.30 * ordered[rank] / (len(ordered) - 1)
    return projects, ratings


def session_path(csv_path):
    """Give each CSV its own checkpoint beside the input file."""
    path = Path(csv_path).resolve()
    return path.with_name(path.name + ".ranker-session.json")
