"""Social groups distribution parser is defined here."""
from __future__ import annotations

import itertools
import json
from dataclasses import dataclass
from typing import Any

from loguru import logger

from population_restorator.models import SocialGroupsDistribution
from population_restorator.models.social_groups import SocialGroupWithProbability


@dataclass
class _TmpSocialGroupInfo:
    """Temporary social group distribution container"""

    name: str
    ages_men: list[float | int] | float
    ages_women: list[float | int] | float
    total: int | float


def parse_distribution(
    filename: str,
) -> SocialGroupsDistribution:
    """Parse given json file to a `SocialGroupsDistribution`.

    Raise `RuntimeError` in case of any unexpected situation.
    """
    primary, additional, ages = _parse_to_tmp(filename)
    if len(primary) == 0 or len(additional) == 0:
        return SocialGroupsDistribution([], [])

    for s_g in itertools.chain(primary, additional):
        if isinstance(s_g.ages_men, float) and isinstance(s_g.ages_women, float):
            s_g.ages_men = [s_g.ages_men / ages for _ in ages]
            s_g.ages_women = [s_g.ages_women / ages for _ in ages]

    total_sgs_number = sum(sg.total for sg in primary)
    if total_sgs_number < 1:
        raise RuntimeError(f"Wrong summary probability of social groups: {total_sgs_number}")

    if total_sgs_number == 1:
        if any(sg.total > 1 for sg in additional):
            s_g: _TmpSocialGroupInfo = next(filter(lambda x: x.total > 1))
            raise RuntimeError(
                f"Social group '{s_g.name}' total value is absolute ({s_g.total}) while primary social groups"
                " total are in a relative form"
            )

    if any(sg.total > 1 for sg in additional) and any(sg.total <= 1 for sg in additional):
        logger.warning(
            "Additional social groups distrbution may be set incorrectly as there are both absolute and relation values"
        )

    res_primary = [
        SocialGroupWithProbability.from_values(sg.name, sg.total / total_sgs_number, sg.ages_men, sg.ages_women)
        for sg in primary
    ]
    res_additional = [
        SocialGroupWithProbability.from_values(sg.name, sg.total / total_sgs_number, sg.ages_men, sg.ages_women)
        for sg in additional
    ]
    return SocialGroupsDistribution(res_primary, res_additional)


def _parse_to_tmp(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    filename: str,
) -> tuple[list[_TmpSocialGroupInfo], list[_TmpSocialGroupInfo]]:
    """Parse given file to temporary social groups distribution class checking for errors.

    Return tuple of (primary, additional, ages): primary and additional social groups as _TmpSocialGroupInfo lists and
    number or ages in lists.
    """
    with open(filename, encoding="utf-8") as file:
        data = json.load(file)

    if not (isinstance(data, dict) and isinstance(data.get("social_groups"), list)):
        logger.error(f"json data read as {type(data)}, 'social_groups' type is {type(data.get('social_groups'))}")
        raise RuntimeError(
            f"{filename} is not a valid social groups distribution file" ' (needed structure: {"social_groups": ...})'
        )

    social_groups: list[dict[str, Any]] = data["social_groups"]

    ages: int | None = None

    logger.debug("Parsing {} social groups distribution", len(social_groups))

    primary_sgs: list[_TmpSocialGroupInfo] = []
    additional_sgs: list[_TmpSocialGroupInfo] = []

    if len(social_groups) == 0:
        logger.warning("No social groups were given in file {}", filename)
        return [], [], 100

    for i, s_g in enumerate(social_groups):
        if "name" not in s_g:
            raise RuntimeError(f"Social group #{i} dos not have a name")
        sg_name = s_g["name"]

        if "ages_men" not in s_g or "ages_women" not in s_g:
            raise RuntimeError(f"Social group '{sg_name}' (#{i}) does not have 'ages_men' or 'ages_women' attribute")

        is_additional = s_g.get("is_additional", False)
        ages_men, ages_women = s_g["ages_men"], s_g["ages_women"]
        total = s_g.get("total")

        if not isinstance(ages_men, list) or not isinstance(ages_women, list):
            if isinstance(ages_men, float) and isinstance(ages_women, float) and ages_men + ages_women == 1:
                logger.warning(
                    "Social group '{}' (#{}) ages_men and ages_women are set by total percentage", sg_name, i
                )
            else:
                if isinstance(ages_men, int) and isinstance(ages_women, int):
                    logger.warning(
                        "Social group '{}' (#{}) ages_men and ages_women are set by a total number of representatives"
                    )
                    if total is None:
                        total = ages_men + ages_women
                    ages_men, ages_women = ages_men / (ages_men + ages_women), ages_women / (ages_men + ages_women)
                else:
                    raise RuntimeError(f"Social group '{sg_name}' (#{i}) 'ages_men' or 'ages_women' is incorrect")
            if total is None:
                raise RuntimeError(
                    f"Social group '{sg_name}' (#{i}) has 'ages_men' and 'ages_women' set as sex probability"
                    " distributions, but no total number of social group representative is given"
                )
        else:
            if ages is None:
                ages = len(ages_men)
            if len(ages_men) != len(ages_women) or len(ages_men) != ages:
                raise RuntimeError(
                    f"Social group '{sg_name}' (#{i}) length of ages_men ({len(ages_men)}) or ages_women ({ages_women})"
                    f" are not equal to number of ages of other social groups ({ages})"
                )

            s_m = sum(ages_men)
            s_w = sum(ages_women)
            if s_m != 1 or s_w != 1:
                if s_m == 1 or s_w == 1:
                    raise RuntimeError(
                        f"Social group '{sg_name}' (#{i}) 'ages_men' and 'ages_women' are set in different styles"
                        " (one is absolute and the other is relative)"
                    )
                if total is None:
                    total = s_m + s_w
                else:
                    if total != s_m + s_w:
                        raise RuntimeError(
                            f"Social group '{sg_name}' total ({total}) differs from sum of 'ages_men' ({s_m})"
                            f" and 'ages_women' ({s_w})"
                        )

        sg_tmp = _TmpSocialGroupInfo(sg_name, ages_men, ages_women, total)
        if is_additional:
            additional_sgs.append(sg_tmp)
        else:
            primary_sgs.append(sg_tmp)

    if len(primary_sgs) == 0 and len(additional_sgs) != 0:
        raise RuntimeError(f"Parsed {len(additional_sgs)}, but no primary social groups to get the distribution")

    if ages is None:
        raise RuntimeError("Ages were not set for all of the social groups.")
    return primary_sgs, additional_sgs, ages
