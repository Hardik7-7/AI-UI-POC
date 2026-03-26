import os
from langchain_google_genai import ChatGoogleGenerativeAI
from src.models.schemas import TestSuite
from dotenv import load_dotenv

load_dotenv()

class TestGenerator:
    def __init__(self, model_name="gemini-2.5-flash"):
        self.llm = ChatGoogleGenerativeAI(model=model_name, temperature=0.1)
    
    def generate_scenarios_from_file(self, file_path: str) -> TestSuite:
        with open(file_path, 'r', encoding='utf-8') as f:
            workflow_content = f.read()

        prompt = f"""
You are an expert QA Engineer. Analyze the following workflow and generate a set of
PROGRESSIVE, SELF-CONTAINED test scenarios.

## Scenario Design Rules

1. **Progressive coverage**: Break the workflow into multiple scenarios that build in scope:
   - Scenario 1: covers only the first logical checkpoint (e.g., login + navigate)
   - Scenario 2: covers from the start up to the second checkpoint (e.g., login + navigate + create)
   - Scenario N: covers the full end-to-end flow
   Each subsequent scenario covers MORE of the workflow.

2. **Self-contained (no dependencies)**: Every scenario MUST start from scratch.
   - Each scenario begins with login and any required setup steps.
   - NO scenario can rely on data or state created by a previous scenario.
   - If a later scenario needs a created item (e.g., a library image), it must CREATE it itself first.

3. **Descriptive naming**: Use clear, action-verb names that describe WHAT the scenario verifies:
   - Good: `verify_login_and_library_navigation`
   - Good: `verify_library_image_created_successfully`
   - Good: `verify_library_image_deployed_and_stopped`
   - Bad: `test_1`, `e2e_flow`, `full_test`

4. For each scenario, produce TWO representations:
   a. `steps`: structured list with action/value/assert for human review
   b. `natural_language_task`: a single detailed paragraph for the AI browser agent

5. Set `navigate_url` to the application's starting URL.

## Workflow to analyze:
{workflow_content}
"""

        structured_llm = self.llm.with_structured_output(TestSuite)
        result = structured_llm.invoke(prompt)
        return result
