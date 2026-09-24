"""The failure categories. Used verbatim in the judge prompt and in label mode."""

from pydantic import BaseModel


class Category(BaseModel):
    id: str
    label: str
    definition: str


CATEGORIES = [
    Category(id="wrong_location", label="Wrong location",
             definition="Changed code in the wrong file or function; the real fix lives elsewhere."),
    Category(id="incomplete_fix", label="Incomplete fix",
             definition="Right place, but the change misses a case or part of the required behaviour."),
    Category(id="broke_other_behaviour", label="Broke other behaviour",
             definition="Fixes the reported case but breaks something that worked before."),
    Category(id="misread_issue", label="Misread the issue",
             definition="Solved a different problem from the one described."),
    Category(id="never_verified", label="Never checked its work",
             definition="Submitted without reproducing the bug or running relevant tests."),
    Category(id="gave_up_or_ran_out", label="Gave up or ran out",
             definition="Stopped early, looped, or hit a step or context limit before finishing."),
    Category(id="tool_or_syntax_trouble", label="Tool or syntax trouble",
             definition="Edits failed to apply, left syntax errors, or the agent fought its tools."),
    Category(id="other", label="Other",
             definition="None of the above; the reason says why."),
]

CATEGORY_IDS = [c.id for c in CATEGORIES]
