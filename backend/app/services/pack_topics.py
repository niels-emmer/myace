"""Derive a pack's "topics" from the tags on its items.

Packs have no tags column (AGENTS.md rule 18); items do. The tag a pack uses
most is nearly always its subject (`python`, `go`, `kubernetes`, `aws`), so the
top few tags, minus generic process words, make a usable topic facet without a
migration, and they work for user-published packs too. Pure functions, so the
rule is unit-tested without a database.
"""

from collections import Counter
from collections.abc import Iterable

# Tags that describe how an item is written rather than what a pack is about.
TOPIC_STOPLIST = frozenset(
    {
        "architecture",
        "build",
        "checklist",
        "design",
        "naming",
        "process",
        "quality",
        "review",
        "services",
        "state",
        "style",
        "tagging",
        "workflow",
    }
)


def derive_topics(
    tag_lists: Iterable[Iterable[str]], *, limit: int = 3, min_count: int = 2
) -> list[str]:
    """The most common meaningful tags across a pack's items, most common first.

    A tag must appear on at least `min_count` items, so a one-off tag never
    becomes a facet. Ties break alphabetically so the order is stable.
    """
    counts: Counter[str] = Counter()
    for tags in tag_lists:
        for tag in {str(t).strip().lower() for t in tags}:
            if not tag or tag.startswith("mode:") or tag in TOPIC_STOPLIST:
                continue
            counts[tag] += 1
    eligible = [(tag, n) for tag, n in counts.items() if n >= min_count]
    eligible.sort(key=lambda pair: (-pair[1], pair[0]))
    return [tag for tag, _ in eligible[:limit]]
