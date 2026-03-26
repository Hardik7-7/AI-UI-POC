from pydantic import BaseModel, Field
from typing import List, Optional

class TestStep(BaseModel):
    step: int = Field(description="Step number, starting from 1")
    action: str = Field(description="Action type, e.g. open_url, click, input, assert, wait, scroll")
    value: Optional[str] = Field(description="The value for the action, e.g. URL, text to type, element label", default=None)
    assert_: Optional[str] = Field(description="What to assert after this action, e.g. page_opened, element_visible, text_present", default=None, alias="assert")

    class Config:
        populate_by_name = True

class TestScenario(BaseModel):
    scenario_name: str = Field(description="A descriptive name for the test, safe for python function name (e.g. test_login_success)")
    description: str = Field(description="Brief objective of the scenario")
    navigate_url: str = Field(description="The initial URL to start the test from, if applicable", default="")
    steps: List[TestStep] = Field(description="Ordered list of human-readable steps with action/value/assert for UI review", default=[])
    natural_language_task: Optional[str] = Field(
        description="The complete step-by-step task string for the AI agent. If omitted, it will be auto-generated from `steps`.",
        default=None
    )

class TestSuite(BaseModel):
    scenarios: List[TestScenario] = Field(description="A list of scenarios extracted from the workflow")
