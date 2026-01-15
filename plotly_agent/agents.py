"""
Specialized agents for code generation.
Implements Orchestrator, Planner, Coder, and Critic agents.
"""

import json
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from openai import OpenAI
import pandas as pd

from .models import (
    Message, AgentAction, AskClarification, RouteToAgent,
    GenerateResponse, Question, PlotSpecification, Encoding,
    Styling, CodeArtifact, CriticResult, Diagnosis
)
from .memory import MemoryManager
from .knowledge import KnowledgeBase
from .tools import ToolRegistry


# ============================================================================
# Base Agent Class
# ============================================================================

class BaseAgent(ABC):
    """Base class for all agents"""

    def __init__(
        self,
        name: str,
        model: str,
        api_key: str,
        temperature: float = 0.0
    ):
        self.name = name
        self.model = model
        self.client = OpenAI(api_key=api_key)
        self.temperature = temperature

    @abstractmethod
    def process(self, *args, **kwargs) -> Any:
        """Main processing logic for the agent"""
        pass

    def _call_llm(
        self,
        messages: List[Dict[str, str]],
        response_format: Optional[Dict] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        Call LLM with messages.

        Args:
            messages: List of message dicts with role and content
            response_format: Optional response format for structured output
            temperature: Override default temperature

        Returns:
            LLM response content
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature
        }

        if response_format:
            kwargs["response_format"] = response_format

        response = self.client.chat.completions.create(**kwargs)

        return response.choices[0].message.content

    def _extract_json(self, text: str) -> Optional[Dict]:
        """Extract JSON from LLM response, handling code blocks"""
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting from code block
        import re
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding JSON anywhere in text
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        return None


# ============================================================================
# Orchestrator Agent
# ============================================================================

class OrchestratorAgent(BaseAgent):
    """
    Routes messages, detects ambiguity, and manages agent collaboration.
    """

    def __init__(self, model: str, api_key: str):
        super().__init__(name="orchestrator", model=model, api_key=api_key)

    def process(
        self,
        message: Message,
        memory: MemoryManager,
        session_id: str,
        data_available: bool = False
    ) -> AgentAction:
        """
        Process message and determine next action.

        Returns:
            AgentAction (AskClarification, RouteToAgent, or GenerateResponse)
        """
        # Get conversation context
        context = memory.get_conversation_context(session_id)

        # 1. Detect ambiguity
        ambiguity_score, ambiguity_reasons = self._detect_ambiguity(
            message, context, data_available
        )

        if ambiguity_score > 0.5:
            questions = self._generate_clarifications(message, ambiguity_reasons, data_available)
            return AskClarification(questions=questions)

        # 2. Classify intent
        intent = self._classify_intent(message, context)

        # 3. Route to appropriate agent
        if intent == "new_plot":
            return RouteToAgent(target_agent="planner", context={"task": "new_plot"})
        elif intent == "modify_plot":
            return RouteToAgent(target_agent="planner", context={"task": "modify_plot"})
        elif intent == "explain":
            return RouteToAgent(target_agent="critic", context={"task": "explain"})
        elif intent == "general_question":
            return GenerateResponse(
                content="I can help you create Plotly visualizations. Please describe what kind of plot you'd like to create."
            )
        else:
            return RouteToAgent(target_agent="planner", context={"task": "general"})

    def _detect_ambiguity(
        self,
        message: Message,
        context: str,
        data_available: bool
    ) -> tuple[float, List[str]]:
        """
        Detect ambiguity in user message.

        Returns:
            (ambiguity_score, reasons) where score is 0-1
        """
        reasons = []
        indicators = []

        content_lower = message.content.lower()

        # Check for missing data source
        if not data_available:
            indicators.append(0.9)
            reasons.append("no_data_source")

        # Check for missing chart type
        chart_keywords = ['scatter', 'line', 'bar', 'histogram', 'box', 'heatmap', 'plot', 'chart', 'graph']
        if not any(word in content_lower for word in chart_keywords):
            indicators.append(0.6)
            reasons.append("no_chart_type")

        # Check for vague terms
        vague_terms = ['nice', 'good', 'better', 'pretty', 'interesting', 'something']
        if any(term in content_lower for term in vague_terms):
            indicators.append(0.4)
            reasons.append("vague_terms")

        # Check for under-specification (very short requests)
        if len(message.content.split()) < 5:
            indicators.append(0.5)
            reasons.append("too_brief")

        # Check for conflicting requirements
        conflicts = [
            ('simple', 'detailed'), ('minimal', 'comprehensive'),
            ('quick', 'thorough'), ('basic', 'advanced')
        ]
        for term1, term2 in conflicts:
            if term1 in content_lower and term2 in content_lower:
                indicators.append(0.7)
                reasons.append("conflicting_requirements")
                break

        # Calculate overall score
        if not indicators:
            return 0.0, []

        ambiguity_score = max(indicators)  # Use max for conservative approach

        return ambiguity_score, reasons

    def _generate_clarifications(
        self,
        message: Message,
        reasons: List[str],
        data_available: bool
    ) -> List[Question]:
        """Generate clarification questions based on ambiguity reasons"""
        questions = []

        if "no_data_source" in reasons:
            questions.append(Question(
                text="I don't have a dataset loaded. Please upload a CSV file first.",
                type="data_source",
                required=True
            ))

        if "no_chart_type" in reasons and data_available:
            questions.append(Question(
                text="What type of visualization would you like to create?",
                type="chart_type",
                options=["scatter", "line", "bar", "histogram", "box", "heatmap"],
                required=True
            ))

        if "vague_terms" in reasons or "too_brief" in reasons:
            questions.append(Question(
                text="Could you provide more details about what you want to visualize? For example, which columns should be on the x and y axes?",
                type="details",
                required=False
            ))

        return questions

    def _classify_intent(self, message: Message, context: str) -> str:
        """
        Classify user intent.

        Returns:
            Intent category: new_plot, modify_plot, explain, general_question
        """
        content_lower = message.content.lower()

        # Modification keywords
        if any(word in content_lower for word in ['change', 'modify', 'update', 'fix', 'adjust', 'different']):
            if 'plot' in context.lower() or 'chart' in context.lower():
                return "modify_plot"

        # Explanation keywords
        if any(word in content_lower for word in ['explain', 'why', 'how does', 'what does', 'tell me about']):
            return "explain"

        # New plot keywords
        if any(word in content_lower for word in ['create', 'make', 'generate', 'show', 'plot', 'visualize', 'chart']):
            return "new_plot"

        # General question
        if '?' in message.content and len(message.content.split()) < 15:
            return "general_question"

        # Default to new plot
        return "new_plot"


# ============================================================================
# Planner Agent
# ============================================================================

class PlannerAgent(BaseAgent):
    """
    Decomposes user request into structured plot specification.
    Uses chain-of-thought reasoning to determine best visualization.
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        knowledge_base: KnowledgeBase
    ):
        super().__init__(name="planner", model=model, api_key=api_key, temperature=0.1)
        self.knowledge_base = knowledge_base

    def process(
        self,
        message: Message,
        data_summary: Dict[str, Any],
        context: str,
        previous_spec: Optional[PlotSpecification] = None
    ) -> PlotSpecification:
        """
        Generate plot specification from user message.

        Args:
            message: User message
            data_summary: Summary of available data
            context: Conversation context
            previous_spec: Previous specification if modifying

        Returns:
            PlotSpecification with chart type, encoding, and styling
        """
        # Retrieve relevant knowledge
        knowledge_context = self.knowledge_base.get_context_string(
            message.content,
            top_k=2,
            max_chars=1500
        )

        # Build prompt
        prompt = self._build_planning_prompt(
            message, data_summary, context, knowledge_context, previous_spec
        )

        # Call LLM with CoT
        response = self._call_llm([
            {"role": "system", "content": "You are an expert data visualization planner."},
            {"role": "user", "content": prompt}
        ])

        # Parse response to extract specification
        spec = self._parse_specification(response, data_summary)

        return spec

    def _build_planning_prompt(
        self,
        message: Message,
        data_summary: Dict[str, Any],
        context: str,
        knowledge: str,
        previous_spec: Optional[PlotSpecification]
    ) -> str:
        """Build comprehensive planning prompt"""

        # Format data schema
        columns_info = []
        for col, info in data_summary.get('columns', {}).items():
            col_desc = f"- {col} ({info['dtype']}): {info['unique_count']} unique values"
            if info.get('sample_values'):
                samples = ', '.join(str(v) for v in info['sample_values'][:3])
                col_desc += f", samples: [{samples}]"
            columns_info.append(col_desc)

        data_schema = "\n".join(columns_info)

        modification_context = ""
        if previous_spec:
            modification_context = f"""
## Current Plot Specification
The user has an existing {previous_spec.chart_type} chart and wants to modify it.
Previous encoding: x={previous_spec.encoding.x}, y={previous_spec.encoding.y}, color={previous_spec.encoding.color}
"""

        prompt = f"""# Task: Plan a Plotly Visualization

{knowledge}

## Data Schema
Total rows: {data_summary.get('total_rows', 'unknown')}
Available columns:
{data_schema}

## User Request
{message.content}

{modification_context}

## Conversation Context
{context}

## Instructions
Think step-by-step to create the best visualization:

1. **Understand Intent**: What is the user trying to learn or communicate?
2. **Choose Chart Type**: Which Plotly chart type best serves this purpose?
3. **Map Encodings**: Which columns should map to x, y, color, size, etc.?
4. **Design Styling**: What title, labels, and colors will make it clear?
5. **Consider Alternatives**: What other approaches could work?

## Output Format
Provide your reasoning, then output a JSON specification:

```json
{{
  "chart_type": "scatter|line|bar|histogram|box|heatmap|pie",
  "encoding": {{
    "x": "column_name or null",
    "y": "column_name or null",
    "color": "column_name or null",
    "size": "column_name or null",
    "aggregation": "mean|sum|count or null"
  }},
  "styling": {{
    "title": "Chart Title",
    "x_label": "X Axis Label",
    "y_label": "Y Axis Label",
    "template": "plotly_white"
  }},
  "reasoning": "Brief explanation of your choices",
  "confidence": 0.9,
  "alternatives": ["alternative approach 1", "alternative approach 2"]
}}
```

Think carefully and output your specification.
"""

        return prompt

    def _parse_specification(
        self,
        response: str,
        data_summary: Dict[str, Any]
    ) -> PlotSpecification:
        """Parse LLM response into PlotSpecification"""

        # Extract JSON from response
        spec_dict = self._extract_json(response)

        if not spec_dict:
            # Fallback: create basic scatter plot
            columns = list(data_summary.get('columns', {}).keys())
            return PlotSpecification(
                chart_type="scatter",
                data_source="df",
                encoding=Encoding(
                    x=columns[0] if columns else None,
                    y=columns[1] if len(columns) > 1 else None
                ),
                styling=Styling(title="Visualization"),
                reasoning="Failed to parse specification, using default",
                confidence=0.3
            )

        # Build specification from dict
        try:
            spec = PlotSpecification(
                chart_type=spec_dict.get('chart_type', 'scatter'),
                data_source="df",
                encoding=Encoding(**spec_dict.get('encoding', {})),
                styling=Styling(**spec_dict.get('styling', {})),
                reasoning=spec_dict.get('reasoning', ''),
                confidence=spec_dict.get('confidence', 0.8),
                alternatives=spec_dict.get('alternatives', [])
            )

            return spec

        except Exception as e:
            # Fallback on error
            columns = list(data_summary.get('columns', {}).keys())
            return PlotSpecification(
                chart_type="scatter",
                data_source="df",
                encoding=Encoding(
                    x=columns[0] if columns else None,
                    y=columns[1] if len(columns) > 1 else None
                ),
                styling=Styling(title="Visualization"),
                reasoning=f"Error parsing specification: {str(e)}",
                confidence=0.3
            )


# ============================================================================
# Coder Agent
# ============================================================================

class CoderAgent(BaseAgent):
    """
    Translates plot specification into executable Plotly code.
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        knowledge_base: KnowledgeBase
    ):
        super().__init__(name="coder", model=model, api_key=api_key, temperature=0.0)
        self.knowledge_base = knowledge_base

    def process(
        self,
        spec: PlotSpecification,
        data_summary: Optional[Dict[str, Any]] = None
    ) -> CodeArtifact:
        """
        Generate Plotly code from specification.

        Args:
            spec: Plot specification
            data_summary: Optional data summary for validation

        Returns:
            CodeArtifact with Python code
        """
        # Retrieve code examples
        examples = self.knowledge_base.search(
            query=f"{spec.chart_type} plot example",
            top_k=1
        )

        example_code = examples[0].content if examples else ""

        # Build prompt
        prompt = self._build_coding_prompt(spec, example_code, data_summary)

        # Call LLM
        response = self._call_llm([
            {"role": "system", "content": "You are an expert Python developer specializing in Plotly."},
            {"role": "user", "content": prompt}
        ])

        # Extract code
        code = self._extract_code(response)

        return CodeArtifact(
            code=code,
            spec=spec,
            metadata={"examples_used": len(examples)}
        )

    def _build_coding_prompt(
        self,
        spec: PlotSpecification,
        example: str,
        data_summary: Optional[Dict[str, Any]]
    ) -> str:
        """Build code generation prompt"""

        spec_json = json.dumps({
            "chart_type": spec.chart_type,
            "encoding": {
                "x": spec.encoding.x,
                "y": spec.encoding.y,
                "color": spec.encoding.color,
                "size": spec.encoding.size,
                "aggregation": spec.encoding.aggregation
            },
            "styling": {
                "title": spec.styling.title,
                "x_label": spec.styling.x_label,
                "y_label": spec.styling.y_label,
                "template": spec.styling.template
            }
        }, indent=2)

        data_context = ""
        if data_summary:
            data_context = f"""
## Data Context
Total rows: {data_summary.get('total_rows', 'unknown')}
Relevant columns: {', '.join(data_summary.get('columns', {}).keys())}
"""

        prompt = f"""# Task: Generate Plotly Code

## Plot Specification
{spec_json}

{data_context}

{example}

## Instructions
Generate clean, executable Python code using Plotly to create this visualization.

Requirements:
- Use plotly.express (px) for simplicity when possible
- The dataframe is available as 'df'
- Store the figure in a variable named 'fig'
- Include all specified encodings and styling
- Handle None values gracefully
- Do NOT include fig.show() - just create the figure
- Add brief comments for clarity

## Output Format
Provide ONLY the Python code, no explanations:

```python
import plotly.express as px

# Your code here
fig = px.scatter(...)
```
"""

        return prompt

    def _extract_code(self, response: str) -> str:
        """Extract Python code from LLM response"""
        import re

        # Try extracting from code block
        code_match = re.search(r'```python\s*(.*?)```', response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # Try finding any code block
        code_match = re.search(r'```\s*(.*?)```', response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # Return full response if no code block found
        return response.strip()


# ============================================================================
# Critic Agent
# ============================================================================

class CriticAgent(BaseAgent):
    """
    Validates code and provides quality assessment and suggestions.
    """

    def __init__(self, model: str, api_key: str):
        super().__init__(name="critic", model=model, api_key=api_key, temperature=0.0)

    def process(
        self,
        artifact: CodeArtifact,
        data_summary: Optional[Dict[str, Any]] = None,
        validate_execution: bool = False
    ) -> CriticResult:
        """
        Evaluate code quality and provide feedback.

        Args:
            artifact: Code artifact to evaluate
            data_summary: Optional data summary for validation
            validate_execution: Whether to validate execution (not used if system just returns code)

        Returns:
            CriticResult with quality assessment
        """
        # 1. Static code analysis
        syntax_ok, syntax_error = self._check_syntax(artifact.code)

        if not syntax_ok:
            diagnosis = Diagnosis(
                error_type="SyntaxError",
                likely_cause="Invalid Python syntax",
                fix_strategy="Fix syntax errors",
                suggested_changes=[syntax_error]
            )

            # Generate fix
            fixed_code = self._fix_syntax_error(artifact.code, syntax_error)

            return CriticResult(
                status="error",
                error=syntax_error,
                diagnosis=diagnosis,
                suggested_fix=fixed_code
            )

        # 2. Validate against specification
        spec_issues = self._validate_against_spec(artifact.code, artifact.spec)

        # 3. Check best practices
        suggestions = self._check_best_practices(artifact.code, artifact.spec)

        # 4. Calculate quality score
        quality_score = self._calculate_quality_score(artifact.code, spec_issues, suggestions)

        if spec_issues:
            return CriticResult(
                status="warning",
                quality_score=quality_score,
                suggestions=spec_issues + suggestions
            )

        return CriticResult(
            status="success",
            quality_score=quality_score,
            suggestions=suggestions
        )

    def _check_syntax(self, code: str) -> tuple[bool, Optional[str]]:
        """Check if code has valid Python syntax"""
        try:
            compile(code, '<string>', 'exec')
            return True, None
        except SyntaxError as e:
            return False, f"Syntax error at line {e.lineno}: {e.msg}"

    def _validate_against_spec(
        self,
        code: str,
        spec: PlotSpecification
    ) -> List[str]:
        """Validate code implements specification correctly"""
        issues = []

        # Check if chart type is mentioned
        chart_funcs = {
            "scatter": "px.scatter",
            "line": "px.line",
            "bar": "px.bar",
            "histogram": "px.histogram",
            "box": "px.box",
            "heatmap": "px.imshow",
        }

        expected_func = chart_funcs.get(spec.chart_type)
        if expected_func and expected_func not in code:
            issues.append(f"Code should use {expected_func} for {spec.chart_type} chart")

        # Check if x/y encodings are present
        if spec.encoding.x and f"x='{spec.encoding.x}'" not in code and f'x="{spec.encoding.x}"' not in code:
            issues.append(f"Missing x-axis encoding: {spec.encoding.x}")

        if spec.encoding.y and f"y='{spec.encoding.y}'" not in code and f'y="{spec.encoding.y}"' not in code:
            issues.append(f"Missing y-axis encoding: {spec.encoding.y}")

        return issues

    def _check_best_practices(
        self,
        code: str,
        spec: PlotSpecification
    ) -> List[str]:
        """Check code follows best practices"""
        suggestions = []

        # Check for title
        if 'title=' not in code and spec.styling.title:
            suggestions.append("Consider adding a title to the figure")

        # Check for proper imports
        if 'import plotly' not in code:
            suggestions.append("Missing plotly import statement")

        # Check for fig variable
        if 'fig =' not in code:
            suggestions.append("Code should assign figure to 'fig' variable")

        return suggestions

    def _calculate_quality_score(
        self,
        code: str,
        issues: List[str],
        suggestions: List[str]
    ) -> float:
        """Calculate overall quality score"""
        base_score = 1.0

        # Deduct for issues
        base_score -= len(issues) * 0.2

        # Deduct slightly for suggestions
        base_score -= len(suggestions) * 0.05

        return max(0.0, min(1.0, base_score))

    def _fix_syntax_error(self, code: str, error: str) -> str:
        """Attempt to fix syntax error using LLM"""
        prompt = f"""# Task: Fix Syntax Error

## Code with Error
```python
{code}
```

## Error
{error}

## Instructions
Fix the syntax error and return the corrected code.
Output ONLY the fixed Python code in a code block.
"""

        response = self._call_llm([
            {"role": "system", "content": "You are a Python expert fixing syntax errors."},
            {"role": "user", "content": prompt}
        ])

        return self._extract_code(response)

    def _extract_code(self, response: str) -> str:
        """Extract code from LLM response"""
        import re

        code_match = re.search(r'```python\s*(.*?)```', response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        code_match = re.search(r'```\s*(.*?)```', response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        return response.strip()
