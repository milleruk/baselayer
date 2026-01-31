from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
from typing import Any

import re
import urllib.request

from django.db.models import Count

from workouts.models import Instructor, RideDetail


INSTRUCTORS_SOURCE_URL = (
    "https://raw.githubusercontent.com/jloss2-ui/peloton-instructor-recommender/"
    "refs/heads/main/lib/instructors.ts"
)

LOCAL_INSTRUCTORS_JSON_PATH = Path(__file__).resolve().parent / "data" / "pelovibe_instructors.json"


def _clean_tag(tag: str) -> str:
    s = str(tag or "").strip()
    if s.startswith("#"):
        s = s[1:]
    return s


def _clean_title(s: str) -> str:
    # Preserve original casing for acronyms like HIIT/EDM when present.
    s = (s or "").strip()
    s = s.replace("_", " ")
    return s


@dataclass(frozen=True)
class PeloVibeInstructor:
    name: str
    modality: list[str]
    language: str
    styles: list[str]
    music: list[str]
    community_tag: str
    description: str


@dataclass(frozen=True)
class CandidateResult:
    name: str
    image_url: str
    score: float
    message: str
    sections: dict[str, list[str]]
    vibe: str | None = None


def _extract_str(obj_text: str, key: str) -> str:
    # Handles escaped quotes: \' inside single-quoted strings
    m = re.search(rf"{re.escape(key)}\s*:\s*'((?:\\\'|[^'])*)'\s*", obj_text)
    if not m:
        return ""
    return m.group(1).replace("\\'", "'").strip()


def _extract_list(obj_text: str, key: str) -> list[str]:
    m = re.search(rf"{re.escape(key)}\s*:\s*\[(.*?)\]\s*", obj_text, re.S)
    if not m:
        return []
    inner = m.group(1)
    items = re.findall(r"'((?:\\\'|[^'])*)'", inner)
    return [it.replace("\\'", "'").strip() for it in items if it.strip()]


def _parse_ts_instructors(ts_text: str) -> list[PeloVibeInstructor]:
    blocks = re.findall(r"\{\s*name:\s*'(?:\\\'|[^'])*'[\s\S]*?\}\s*,", ts_text)
    out: list[PeloVibeInstructor] = []
    for b in blocks:
        name = _extract_str(b, "name")
        if not name:
            continue
        out.append(
            PeloVibeInstructor(
                name=name,
                modality=_extract_list(b, "modality"),
                language=_extract_str(b, "language"),
                styles=_extract_list(b, "styles"),
                music=_extract_list(b, "music"),
                community_tag=_extract_str(b, "community_tag"),
                description=_extract_str(b, "description"),
            )
        )
    return out


def _load_local_instructors_json() -> list[PeloVibeInstructor] | None:
    try:
        if not LOCAL_INSTRUCTORS_JSON_PATH.exists():
            return None
        raw = LOCAL_INSTRUCTORS_JSON_PATH.read_text(encoding="utf-8")
        data = json.loads(raw or "[]")
        if not isinstance(data, list) or len(data) == 0:
            return None
        out: list[PeloVibeInstructor] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            out.append(
                PeloVibeInstructor(
                    name=name,
                    modality=[str(x) for x in (item.get("modality") or []) if str(x).strip()],
                    language=str(item.get("language") or "").strip(),
                    styles=[str(x) for x in (item.get("styles") or []) if str(x).strip()],
                    music=[str(x) for x in (item.get("music") or []) if str(x).strip()],
                    community_tag=str(item.get("community_tag") or "").strip(),
                    description=str(item.get("description") or "").strip(),
                )
            )
        return out if out else None
    except Exception:
        return None


def write_local_instructors_json(source_url: str = INSTRUCTORS_SOURCE_URL) -> int:
    """
    Fetch the upstream instructors.ts and write a normalized JSON file to LOCAL_INSTRUCTORS_JSON_PATH.
    Returns the number of instructors written.
    """
    ts_text = urllib.request.urlopen(source_url, timeout=30).read().decode("utf-8")
    instructors = _parse_ts_instructors(ts_text)
    payload = [
        {
            "name": i.name,
            "modality": i.modality,
            "language": i.language,
            "styles": i.styles,
            "music": i.music,
            "community_tag": i.community_tag,
            "description": i.description,
        }
        for i in instructors
    ]
    LOCAL_INSTRUCTORS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_INSTRUCTORS_JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # clear cache
    load_pelovibe_instructors.cache_clear()
    return len(payload)


@lru_cache(maxsize=1)
def load_pelovibe_instructors() -> list[PeloVibeInstructor]:
    """
    Load curated instructor dataset.
    Prefer local JSON (committed/controlled). If empty/missing, fall back to upstream TS.
    """
    local = _load_local_instructors_json()
    if local:
        return local

    ts_text = urllib.request.urlopen(INSTRUCTORS_SOURCE_URL, timeout=30).read().decode("utf-8")
    return _parse_ts_instructors(ts_text)


def _to_hashtag(s: str) -> str:
    """
    Convert a snake_case label into a repo-like hashtag.
    Example: power_zone -> #PowerZone, low_impact -> #LowImpact
    """
    raw = (s or "").strip()
    if not raw:
        return ""
    # If already a hash tag, keep as-is
    if raw.startswith("#"):
        return raw
    parts = re.split(r"[^0-9A-Za-z]+", raw)
    parts = [p for p in parts if p]
    if not parts:
        return ""
    return "#" + "".join(p[:1].upper() + p[1:] for p in parts)


def _discipline_to_modality_tag(fd: str) -> str:
    fd = (fd or "").strip().lower()
    if not fd:
        return ""
    # Repo uses #Tread for running/walking.
    if fd in ["running", "walking"]:
        return "#Tread"
    if fd in ["cycling", "bike", "ride", "cycling_output_zones"]:
        return "#Cycling"
    if fd in ["strength"]:
        return "#Strength"
    if fd in ["yoga", "stretching"]:
        return "#Yoga/Stretching"
    if fd in ["rowing"]:
        return "#Rowing"
    if fd in ["bootcamp", "bike_bootcamp", "tread_bootcamp"]:
        return "#Bootcamp"
    if fd in ["meditation"]:
        return "#Meditation"
    return _to_hashtag(fd)


@lru_cache(maxsize=16)
def build_db_instructor_profiles(discipline_filter: str | None) -> dict[str, PeloVibeInstructor]:
    """
    Build a lightweight "Pelovibe-style" profile for every instructor we have in the DB
    (so the recommender still works for instructors not in the curated list).
    """
    rd = RideDetail.objects.filter(instructor__isnull=False).select_related("instructor")
    if discipline_filter:
        rd = rd.filter(fitness_discipline__iexact=discipline_filter)

    # Aggregate class types per instructor
    by_instr_styles: dict[str, list[str]] = {}
    for row in (
        rd.exclude(class_type__isnull=True)
        .exclude(class_type__exact="")
        .values("instructor__name", "class_type")
        .annotate(c=Count("id"))
        .order_by("instructor__name", "-c")
        .iterator()
    ):
        name = (row.get("instructor__name") or "").strip()
        if not name:
            continue
        styles = by_instr_styles.setdefault(name.lower(), [])
        tag = _to_hashtag(row.get("class_type") or "")
        if tag and tag not in styles and len(styles) < 6:
            styles.append(tag)

    # Aggregate top disciplines per instructor (used as modality fallback)
    by_instr_mods: dict[str, list[str]] = {}
    for row in (
        rd.exclude(fitness_discipline__isnull=True)
        .exclude(fitness_discipline__exact="")
        .values("instructor__name", "fitness_discipline")
        .annotate(c=Count("id"))
        .order_by("instructor__name", "-c")
        .iterator()
    ):
        name = (row.get("instructor__name") or "").strip()
        if not name:
            continue
        mods = by_instr_mods.setdefault(name.lower(), [])
        tag = _discipline_to_modality_tag(row.get("fitness_discipline") or "")
        if tag and tag not in mods and len(mods) < 3:
            mods.append(tag)

    # Build final profiles for instructors present in DB
    out: dict[str, PeloVibeInstructor] = {}
    for instr in Instructor.objects.all().values_list("name", flat=True).iterator():
        name = (instr or "").strip()
        if not name:
            continue
        key = name.lower()
        out[key] = PeloVibeInstructor(
            name=name,
            modality=by_instr_mods.get(key, []),
            language="",
            styles=by_instr_styles.get(key, []),
            music=[],
            community_tag="",
            description="",
        )

    return out


def _find_by_name(name: str) -> PeloVibeInstructor | None:
    n = (name or "").strip().lower()
    if not n:
        return None
    for instr in load_pelovibe_instructors():
        if instr.name.strip().lower() == n:
            return instr
    # Fallback: construct from our DB-derived profile if present
    return build_db_instructor_profiles(None).get(n)


def _message_for(name: str, shared_styles: list[str]) -> str:
    first = (name.split(" ", 1)[0] if name else "They")
    if shared_styles:
        cleaned = [_clean_tag(s) for s in shared_styles]
        cleaned = [c for c in cleaned if c]
        if len(cleaned) == 1:
            styles_part = f"{cleaned[0].lower()} approach"
        elif len(cleaned) == 2:
            styles_part = f"{cleaned[0].lower()} and {cleaned[1].lower()} style"
        else:
            styles_part = f"{', '.join(s.lower() for s in cleaned[:-1])}, and {cleaned[-1].lower()} training"
        return f"You'll love {first}'s {styles_part}, which matches what you love about your favorite instructors."
    return f"You'll love {first}'s unique training style that offers a fresh perspective."


def recommend_instructors(
    *,
    love_1_name: str,
    love_2_name: str,
    exclude_name: str | None = None,
    discipline_filter: str | None = None,
    limit: int = 3,
) -> list[CandidateResult]:
    i1 = _find_by_name(love_1_name)
    i2 = _find_by_name(love_2_name)
    if not i1 or not i2:
        return []

    liked_styles = set(i1.styles or []) | set(i2.styles or [])

    excluded_names = {i1.name.strip().lower(), i2.name.strip().lower()}
    if exclude_name:
        excluded_names.add(exclude_name.strip().lower())

    # Optional modality filter (single selection like current UI)
    modality_filter = None
    if discipline_filter:
        # Our UI uses "cycling", "strength" etc; dataset uses "#Cycling", etc.
        modality_filter = _clean_title(discipline_filter).strip().lower()

    # Candidate pool: all DB instructors (preferred) plus curated list (in case of missing in DB)
    candidates: dict[str, PeloVibeInstructor] = {}
    candidates.update(build_db_instructor_profiles(discipline_filter).copy())
    for instr in load_pelovibe_instructors():
        candidates.setdefault(instr.name.strip().lower(), instr)

    scored: list[tuple[PeloVibeInstructor, int, list[str]]] = []
    for instr in candidates.values():
        if instr.name.strip().lower() in excluded_names:
            continue
        shared = [s for s in (instr.styles or []) if s in liked_styles]
        score = len(shared)
        if score <= 0:
            continue
        if modality_filter:
            has_mod = any(_clean_tag(m).strip().lower() == modality_filter for m in (instr.modality or []))
            if not has_mod:
                continue
        scored.append((instr, score, shared))

    scored.sort(key=lambda t: t[1], reverse=True)

    # Attach local image URL if we have that instructor in our DB
    image_map = {
        n.lower(): (img or "")
        for n, img in Instructor.objects.filter(name__isnull=False).values_list("name", "image_url")
    }

    results: list[CandidateResult] = []
    for instr, score, shared in scored[: max(1, int(limit))]:
        sections = {
            "modality": [_clean_tag(m) for m in (instr.modality or []) if _clean_tag(m)],
            "language": [_clean_tag(instr.language)] if _clean_tag(instr.language) else [],
            "styles": [_clean_tag(s) for s in (instr.styles or []) if _clean_tag(s)],
            "music": [_clean_tag(s) for s in (instr.music or []) if _clean_tag(s)],
            "community": [_clean_tag(instr.community_tag)] if _clean_tag(instr.community_tag) else [],
        }
        # Cap to match the card density
        sections["modality"] = sections["modality"][:2]
        sections["styles"] = sections["styles"][:4]
        sections["music"] = sections["music"][:3]
        sections["community"] = sections["community"][:1]

        results.append(
            CandidateResult(
                name=instr.name,
                image_url=image_map.get(instr.name.lower(), ""),
                score=float(score),
                message=_message_for(instr.name, shared),
                sections=sections,
                vibe=(instr.description or "").strip() or None,
            )
        )

    return results


def suggest_instructors(
    *,
    q: str,
    discipline_filter: str | None = None,
    limit: int = 12,
) -> list[dict[str, Any]]:
    q = (q or "").strip()
    if len(q) < 2:
        return []
    if len(q) > 64:
        q = q[:64]

    modality_filter = None
    if discipline_filter:
        modality_filter = _clean_title(discipline_filter).strip().lower()

    image_map = {
        n.lower(): (img or "")
        for n, img in Instructor.objects.filter(name__isnull=False).values_list("name", "image_url")
    }

    # Suggestions should include all instructors from our DB; when a curated profile exists,
    # use its tags for the subtitle.
    out: list[dict[str, Any]] = []

    qs = Instructor.objects.all()
    if modality_filter:
        qs = qs.filter(ride_details__fitness_discipline__iexact=modality_filter).distinct()
    qs = qs.filter(name__icontains=q).order_by("name")

    # Precompute DB profiles for subtitle fallback
    db_profiles = build_db_instructor_profiles(modality_filter if modality_filter else None)

    curated_by_name = {i.name.strip().lower(): i for i in load_pelovibe_instructors()}

    for name, img in qs.values_list("name", "image_url")[: max(1, int(limit))]:
        nm = (name or "").strip()
        if not nm:
            continue
        key = nm.lower()
        prof = curated_by_name.get(key) or db_profiles.get(key)
        styles = prof.styles if prof else []
        subtitle = " • ".join(_clean_tag(s) for s in (styles or [])[:4] if _clean_tag(s))
        out.append({"name": nm, "image_url": img or "", "subtitle": subtitle})

    return out

