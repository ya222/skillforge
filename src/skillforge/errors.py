"""Every failure mode is an explicit, named error. Nothing is silently recovered."""


class SkillforgeError(Exception):
    """Base class for every error skillforge raises."""


class ConfigError(SkillforgeError):
    """skillforge.yaml is malformed or self-contradictory."""


class SkillError(SkillforgeError):
    """A SKILL.md is malformed or violates the skill contract."""


class ParamError(SkillforgeError):
    """A param is missing, unknown, or the wrong type."""


class ExprError(SkillforgeError):
    """A `when` expression failed to parse or evaluate."""


class PatchError(SkillforgeError):
    """A patch target was not found, was ambiguous, drifted, or conflicted."""


class SourceError(SkillforgeError):
    """An upstream source could not be fetched or resolved."""


class DriftError(SkillforgeError):
    """Committed output no longer matches what a build produces."""
