"""
New workflow agents for Plotly code generation.
Implements the complete workflow: Communication -> Generator -> Router -> Optimizer -> Verifier
"""

import os
import re
from typing import Dict, Any, Optional, List, Tuple
from openai import OpenAI
import pandas as pd
from pathlib import Path


class BaseAgent:
    """Base class for all workflow agents"""

    def __init__(self, model: str = "gpt-5.2"):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = model
        self.prompts_dir = Path(__file__).parent / "prompts"

    def load_prompt(self, prompt_file: str) -> str:
        """Load prompt from file"""
        prompt_path = self.prompts_dir / prompt_file
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()

    def call_llm(self, messages: List[Dict[str, str]], temperature: Optional[float] = None) -> str:
        """Call OpenAI API"""
        kwargs = {
            "model": self.model,
            "messages": messages,
        }
        # Only set temperature if explicitly provided (some models don't support it)
        if temperature is not None:
            kwargs["temperature"] = temperature
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content


class CommunicationAgent(BaseAgent):
    """Handles user interaction, clarifications, and story collection"""

    def __init__(self):
        super().__init__(model="gpt-5-mini")  # Use mini for conversation
        self.prompt_template = self.load_prompt("communication_agent.txt")

    def chat(self,
             user_message: str,
             conversation_history: List[Dict[str, str]],
             data_summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process user message and determine next action.

        Returns:
            dict with keys:
                - action: 'conversation' | 'needs_data' | 'clarify' | 'ready'
                - message: response message (for conversation, needs_data, clarify)
                - story_summary: story summary (for ready)
        """
        # Build data info string
        if data_summary:
            data_info = f"""
Data uploaded: Yes
Columns: {', '.join(data_summary.get('columns', []))}
Rows: {data_summary.get('shape', (0, 0))[0]}
"""
        else:
            data_info = "Data uploaded: No"

        # Build conversation history string
        history_str = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in conversation_history[-5:]  # Last 5 messages
        ])

        # Fill in prompt
        prompt = self.prompt_template.format(
            data_info=data_info,
            conversation_history=history_str,
            user_message=user_message
        )

        # Call LLM
        response = self.call_llm([
            {"role": "system", "content": prompt}
        ])

        # Parse response
        return self._parse_response(response)

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse agent response into structured format"""
        # Extract action
        action_match = re.search(r'<action>(.*?)</action>', response, re.DOTALL)
        if not action_match:
            # Default to conversation if no action specified
            return {
                'action': 'conversation',
                'message': response
            }

        action = action_match.group(1).strip()

        if action == 'ready':
            # Extract story summary
            story_match = re.search(r'<story_summary>(.*?)</story_summary>', response, re.DOTALL)
            story_summary = story_match.group(1).strip() if story_match else ""
            return {
                'action': 'ready',
                'story_summary': story_summary
            }

        elif action == 'clarify':
            # Extract question
            question_match = re.search(r'<question>(.*?)</question>', response, re.DOTALL)
            question = question_match.group(1).strip() if question_match else ""
            return {
                'action': 'clarify',
                'message': question
            }

        else:  # conversation or needs_data
            # Extract message
            message_match = re.search(r'<message>(.*?)</message>', response, re.DOTALL)
            message = message_match.group(1).strip() if message_match else response
            return {
                'action': action,
                'message': message
            }


class PlotGeneratorAgent(BaseAgent):
    """Generates initial base plot from story summary"""

    def __init__(self):
        super().__init__()
        self.prompt_template = self.load_prompt("plot_generator.txt")

    def generate(self,
                 story_summary: str,
                 data_summary: Dict[str, Any],
                 file_path: str) -> Dict[str, Any]:
        """
        Generate initial plot code.

        Returns:
            dict with keys:
                - chart_type: 'line' | 'bar' | 'scatter' | 'other'
                - reasoning: why this chart type
                - code: generated Python code
                - success: bool
        """
        # Build data summary string
        columns_str = ', '.join(data_summary.get('columns', []))
        dtypes_str = str(data_summary.get('dtypes', {}))
        shape_str = str(data_summary.get('shape', (0, 0)))
        sample_data_str = str(data_summary.get('head', 'No sample available'))

        # Fill in prompt
        prompt = self.prompt_template.format(
            story_summary=story_summary,
            columns=columns_str,
            dtypes=dtypes_str,
            shape=shape_str,
            sample_data=sample_data_str
        )

        # Call LLM
        response = self.call_llm([
            {"role": "system", "content": prompt}
        ], temperature=0.3)

        # Parse response
        return self._parse_response(response, file_path)

    def _parse_response(self, response: str, file_path: str) -> Dict[str, Any]:
        """Parse generator response"""
        # Extract chart type
        chart_match = re.search(r'<chart_type>(.*?)</chart_type>', response, re.DOTALL)
        chart_type = chart_match.group(1).strip() if chart_match else 'other'

        # Extract reasoning
        reasoning_match = re.search(r'<reasoning>(.*?)</reasoning>', response, re.DOTALL)
        reasoning = reasoning_match.group(1).strip() if reasoning_match else ""

        # Extract code
        code_match = re.search(r'<execute_python>(.*?)</execute_python>', response, re.DOTALL)
        code = code_match.group(1).strip() if code_match else ""

        # Replace placeholder with actual file path
        code = code.replace('uploaded_file.csv', file_path)

        return {
            'chart_type': chart_type,
            'reasoning': reasoning,
            'code': code,
            'success': bool(code)
        }


class ChartRouter:
    """Routes to appropriate optimizer based on chart type"""

    CHART_TYPE_MAP = {
        'line': 'line',
        'bar': 'bar',
        'scatter': 'scatter',
        'other': 'scatter'  # Default to scatter for unknown types
    }

    @staticmethod
    def route(chart_type: str) -> str:
        """
        Determine which optimizer to use.

        Returns:
            optimizer name: 'line' | 'bar' | 'scatter'
        """
        return ChartRouter.CHART_TYPE_MAP.get(chart_type.lower(), 'scatter')


class OptimizerAgent(BaseAgent):
    """Base class for chart-type specific optimizers"""

    def __init__(self, chart_type: str):
        super().__init__()
        self.chart_type = chart_type
        self.prompt_template = self.load_prompt(f"{chart_type}_optimizer.txt")

    def optimize(self,
                 story_summary: str,
                 base_code: str,
                 execution_result: str) -> Dict[str, Any]:
        """
        Optimize the base plot.

        Returns:
            dict with keys:
                - improvements: list of improvements made
                - code: optimized code
                - success: bool
        """
        # Fill in prompt
        prompt = self.prompt_template.format(
            story_summary=story_summary,
            base_code=base_code,
            execution_result=execution_result
        )

        # Call LLM
        response = self.call_llm([
            {"role": "system", "content": prompt}
        ], temperature=0.3)

        # Parse response
        return self._parse_response(response)

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse optimizer response"""
        # Extract improvements
        improvements_match = re.search(r'<improvements>(.*?)</improvements>', response, re.DOTALL)
        improvements = improvements_match.group(1).strip() if improvements_match else ""

        # Extract code
        code_match = re.search(r'<execute_python>(.*?)</execute_python>', response, re.DOTALL)
        code = code_match.group(1).strip() if code_match else ""

        return {
            'improvements': improvements,
            'code': code,
            'success': bool(code)
        }


class LineOptimizerAgent(OptimizerAgent):
    """Specialist for line charts"""
    def __init__(self):
        super().__init__('line')


class BarOptimizerAgent(OptimizerAgent):
    """Specialist for bar charts"""
    def __init__(self):
        super().__init__('bar')


class ScatterOptimizerAgent(OptimizerAgent):
    """Specialist for scatter plots"""
    def __init__(self):
        super().__init__('scatter')


class VerifierAgent(BaseAgent):
    """Verifies final code against story requirements"""

    def __init__(self):
        super().__init__()
        self.prompt_template = self.load_prompt("verifier.txt")

    def verify(self,
               story_summary: str,
               optimized_code: str,
               execution_result: str) -> Dict[str, Any]:
        """
        Verify the optimized plot.

        Returns:
            dict with keys:
                - status: 'approved' | 'needs_changes'
                - explanation: explanation of decision
                - issues: list of issues (if needs_changes)
                - final_code: final code (either same or corrected)
                - success: bool
        """
        # Fill in prompt
        prompt = self.prompt_template.format(
            story_summary=story_summary,
            optimized_code=optimized_code,
            execution_result=execution_result
        )

        # Call LLM
        response = self.call_llm([
            {"role": "system", "content": prompt}
        ], temperature=0.3)

        # Parse response
        return self._parse_response(response)

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse verifier response"""
        # Extract status
        status_match = re.search(r'<status>(.*?)</status>', response, re.DOTALL)
        status = status_match.group(1).strip() if status_match else 'approved'

        # Extract explanation or issues
        if status == 'approved':
            explanation_match = re.search(r'<explanation>(.*?)</explanation>', response, re.DOTALL)
            explanation = explanation_match.group(1).strip() if explanation_match else ""
            issues = None
        else:
            issues_match = re.search(r'<issues>(.*?)</issues>', response, re.DOTALL)
            issues = issues_match.group(1).strip() if issues_match else ""
            explanation = f"Changes needed:\n{issues}"

        # Extract final code
        code_match = re.search(r'<final_code>(.*?)</final_code>', response, re.DOTALL)
        final_code = code_match.group(1).strip() if code_match else ""

        return {
            'status': status,
            'explanation': explanation,
            'issues': issues,
            'final_code': final_code,
            'success': bool(final_code)
        }
