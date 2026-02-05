from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from django.utils import timezone

from core.models import SiteSettings
from peloton.models import PelotonConnection

from .models import AnnualChallengeProgress


@dataclass(frozen=True)
class AnnualTier:
    minutes: int
    icon_url: str


TIERS: list[AnnualTier] = [
    AnnualTier(1000, "https://s3.amazonaws.com/challenges-and-tiers-image-prod/ab83be75204140b28719dd6d1d9468ef"),
    AnnualTier(2000, "https://s3.amazonaws.com/challenges-and-tiers-image-prod/75b4b8a9d9494ddca02478bd00e40b79"),
    AnnualTier(3000, "https://s3.amazonaws.com/challenges-and-tiers-image-prod/7024197179b241e3b4eeb297d4f3d0d3"),
    AnnualTier(4000, "https://s3.amazonaws.com/challenges-and-tiers-image-prod/7e2b9cb99cfb45388b325397218de4b3"),
    AnnualTier(5000, "https://s3.amazonaws.com/challenges-and-tiers-image-prod/a9281476443842c1a57bfd95bd98de87"),
    AnnualTier(6000, "https://s3.amazonaws.com/challenges-and-tiers-image-prod/c0f5a1541ff744e89428e3128598e237"),
    AnnualTier(7000, "https://s3.amazonaws.com/challenges-and-tiers-image-prod/c79acb273e9447f892e19342881e9333"),
    AnnualTier(8000, "https://s3.amazonaws.com/challenges-and-tiers-image-prod/2ca45b1d29ef4516a35374332777790d"),
    AnnualTier(9000, "https://s3.amazonaws.com/challenges-and-tiers-image-prod/e00fd9ce07b845329eec2040ab3578aa"),
    AnnualTier(10000, "https://s3.amazonaws.com/challenges-and-tiers-image-prod/e423f7fe15e043c7b346ac0b8e5f68c4"),
    AnnualTier(15000, "https://s3.amazonaws.com/challenges-and-tiers-image-prod/d912a6c2dfd64816a51d25d31db1ca2e"),
    AnnualTier(18000, "https://s3.amazonaws.com/challenges-and-tiers-image-prod/26c7749342cf40f7a4c240511700fa36"),
    AnnualTier(20000, "https://s3.amazonaws.com/challenges-and-tiers-image-prod/4bedb7bc58d1483e9329f23511e7ce22"),
]


def days_in_year(year: int) -> int:
    return (date(year + 1, 1, 1) - date(year, 1, 1)).days


def days_elapsed_in_year(today: date) -> int:
    year_start = date(today.year, 1, 1)
    # inclusive of today
    return (today - year_start).days + 1


@dataclass(frozen=True)
class TierProgress:
    tier: AnnualTier
    progress_pct: float
    is_complete: bool
    label: str
    required_min_per_day: float
    required_min_per_week: float
    needed_min_per_day: float | None
    needed_min_per_week: float | None


def compute_tier_progress(*, minutes_ytd: int, today: date, tiers: Iterable[AnnualTier] = TIERS) -> list[TierProgress]:
    year = today.year
    total_days = days_in_year(year)
    elapsed = min(total_days, max(1, days_elapsed_in_year(today)))
    remaining = max(0, total_days - elapsed + 1)

    out: list[TierProgress] = []
    for tier in tiers:
        pct = (minutes_ytd / tier.minutes) * 100.0 if tier.minutes > 0 else 0.0
        is_complete = minutes_ytd >= tier.minutes
        progress_pct = 100.0 if is_complete else max(0.0, min(100.0, pct))
        label = "Complete!" if is_complete else f"{minutes_ytd} / {tier.minutes}"

        required_per_day = tier.minutes / total_days
        required_per_week = required_per_day * 7.0

        remaining_needed = max(0, tier.minutes - minutes_ytd)
        if remaining == 0:
            needed_per_day: float | None = 0.0 if remaining_needed == 0 else None
        else:
            needed_per_day = remaining_needed / remaining

        needed_per_week: float | None = (needed_per_day * 7.0) if needed_per_day is not None else None

        out.append(
            TierProgress(
                tier=tier,
                progress_pct=progress_pct,
                is_complete=is_complete,
                label=label,
                required_min_per_day=required_per_day,
                required_min_per_week=required_per_week,
                needed_min_per_day=needed_per_day,
                needed_min_per_week=needed_per_week,
            )
        )
    return out


def update_annual_challenge_progress_from_peloton(*, user) -> AnnualChallengeProgress | None:
    settings = SiteSettings.get_settings()
    challenge_id = settings.annual_challenge_id
    if not challenge_id:
        return None

    try:
        connection = PelotonConnection.objects.get(user=user, is_active=True)
    except PelotonConnection.DoesNotExist:
        return None

    try:
        client = connection.get_client()
    except Exception:
        return None

    if not connection.peloton_user_id:
        try:
            user_data = client.fetch_current_user()
            peloton_user_id = user_data.get("id")
            if peloton_user_id:
                connection.peloton_user_id = str(peloton_user_id)
                connection.save(update_fields=["peloton_user_id"])
        except Exception:
            return None

    if not connection.peloton_user_id:
        return None

    try:
        payload = client._get(
            f"/api/user/{connection.peloton_user_id}/challenges/current",
            params={"has_joined": "true"},
        )
    except Exception:
        return None

    challenges = payload.get("challenges", []) if isinstance(payload, dict) else []
    match = None
    for challenge in challenges:
        summary = challenge.get("challenge_summary", {}) if isinstance(challenge, dict) else {}
        if summary.get("id") == challenge_id:
            match = challenge
            break

    now = timezone.now()

    if not match:
        progress, _ = AnnualChallengeProgress.objects.update_or_create(
            user=user,
            challenge_id=challenge_id,
            defaults={
                "minutes_ytd": None,
                "metric_display_value": "",
                "metric_display_unit": "",
                "has_joined": False,
                "challenge_status": "",
                "last_synced_at": now,
            },
        )
        return progress

    progress_data = match.get("progress", {}) if isinstance(match, dict) else {}
    summary = match.get("challenge_summary", {}) if isinstance(match, dict) else {}
    has_joined = bool(progress_data.get("has_joined"))
    minutes_value = progress_data.get("metric_value")
    minutes_ytd = int(minutes_value) if minutes_value is not None and has_joined else None
    metric_display_value = progress_data.get("metric_display_value") or ""
    metric_display_unit = progress_data.get("metric_display_unit") or ""

    progress, _ = AnnualChallengeProgress.objects.update_or_create(
        user=user,
        challenge_id=challenge_id,
        defaults={
            "minutes_ytd": minutes_ytd,
            "metric_display_value": metric_display_value if has_joined else "",
            "metric_display_unit": metric_display_unit if has_joined else "",
            "has_joined": has_joined,
            "challenge_status": summary.get("status") or "",
            "last_synced_at": now,
        },
    )

    return progress

