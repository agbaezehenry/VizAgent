"""
Pydantic models for the Plotly agent system.
Defines data structures for messages, memory, specifications, and tools.
Simplified version - returns only code and text, no figure rendering.
"""

from typing import List, Dict, Any, Optional, Literal, Callable, Type
from datetime import datetime
from pydantic import BaseModel, Field
import pandas as pd


# ============================================================================
# Message Models
# ============================================================================

class Message(BaseModel):
    """Represents a single message in a conversation"""
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    references: List[str] = Field(default_factory=list)  # Co-reference tracking

    class Config:
        arbitrary_types_allowed = True


class Question(BaseModel):
    """Represents a clarification question to ask the user"""
    text: str
    type: str  # data_source, chart_type, encoding, etc.
    options: Optional[List[str]] = None
    required: bool = True


# ============================================================================
# Memory Models
# ============================================================================

class Episode(BaseModel):
    """Compressed representation of past conversation segment"""
    summary: str
    key_facts: List[str]
    user_corrections: List[str]
    timestamp_range: tuple[datetime, datetime]


class Correction(BaseModel):
    """Records user feedback and corrections"""
    original_output: str
    corrected_output: str
    feedback: str
    timestamp: datetime


class UserProfile(BaseModel):
    """Tracks user preferences learned over time"""
    preferred_colors: List[str] = Field(default_factory=lambda: ["#636EFA", "#EF553B", "#00CC96"])
    preferred_chart_types: Dict[str, float] = Field(default_factory=dict)  # type -> frequency
    verbosity_preference: Literal["minimal", "balanced", "detailed"] = "minimal"
    technical_level: Literal["beginner", "intermediate", "advanced"] = "intermediate"
    past_corrections: List[Correction] = Field(default_factory=list)


class WorkingMemory(BaseModel):
    """Short-term memory for current conversation context"""
    current_data: Optional[Any] = None  # pd.DataFrame
    current_data_path: Optional[str] = None
    current_plot_spec: Optional['PlotSpecification'] = None
    current_code: Optional[str] = None
    pending_clarifications: List[Question] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True


class SessionMemory(BaseModel):
    """Complete memory for a conversation session"""
    session_id: str
    messages: List[Message] = Field(default_factory=list)
    working_memory: WorkingMemory = Field(default_factory=WorkingMemory)
    episodic_memory: List[Episode] = Field(default_factory=list)
    user_profile: UserProfile = Field(default_factory=UserProfile)
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        arbitrary_types_allowed = True


# ============================================================================
# Visualization Specification Models
# ============================================================================

class Encoding(BaseModel):
    """Defines how data maps to visual channels"""
    x: Optional[str] = None
    y: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None
    facet_row: Optional[str] = None
    facet_col: Optional[str] = None
    aggregation: Optional[str] = None  # mean, sum, count, etc.
    filters: Dict[str, Any] = Field(default_factory=dict)


class Styling(BaseModel):
    """Visual styling parameters"""
    title: str = "Visualization"
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    color_scale: Optional[str] = None
    template: str = "plotly_white"
    width: int = 800
    height: int = 600
    show_legend: bool = True
    custom_style: Dict[str, Any] = Field(default_factory=dict)


class PlotSpecification(BaseModel):
    """Complete specification for a Plotly visualization"""
    chart_type: Literal[
        "scatter", "line", "bar", "histogram", "box",
        "violin", "heatmap", "3d_scatter", "pie", "sunburst"
    ]
    data_source: str
    encoding: Encoding
    styling: Styling
    reasoning: str = ""  # Chain-of-thought explanation
    confidence: float = 1.0  # How confident the planner is
    alternatives: List[str] = Field(default_factory=list)  # Alternative approaches


# ============================================================================
# Code Artifact Models
# ============================================================================

class CodeArtifact(BaseModel):
    """Generated code with metadata"""
    code: str
    spec: PlotSpecification
    language: str = "python"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    version: int = 1  # For tracking iterations


class Diagnosis(BaseModel):
    """Error diagnosis from Critic agent"""
    error_type: str
    likely_cause: str
    code_location: Optional[str] = None
    fix_strategy: str
    suggested_changes: List[str] = Field(default_factory=list)


class CriticResult(BaseModel):
    """Result from Critic agent evaluation (code validation only, no execution)"""
    status: Literal["success", "error", "warning"]
    quality_score: float = 0.0
    error: Optional[str] = None
    diagnosis: Optional[Diagnosis] = None
    suggested_fix: Optional[str] = None
    suggestions: List[str] = Field(default_factory=list)


# ============================================================================
# Tool Models
# ============================================================================

class Tool(BaseModel):
    """Definition of a tool that agents can use"""
    name: str
    description: str
    parameters_schema: Dict[str, Any]  # JSON schema
    function: Optional[Callable] = None  # Actual implementation

    class Config:
        arbitrary_types_allowed = True


class ToolCall(BaseModel):
    """Request to execute a tool"""
    tool_name: str
    parameters: Dict[str, Any]


class ToolResult(BaseModel):
    """Result from tool execution"""
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0

    class Config:
        arbitrary_types_allowed = True


# ============================================================================
# Agent Action Models
# ============================================================================

class AgentAction(BaseModel):
    """Base class for agent actions"""
    action_type: str


class AskClarification(AgentAction):
    """Request clarification from user"""
    action_type: str = "ask_clarification"
    questions: List[Question]


class RouteToAgent(AgentAction):
    """Route message to specific agent"""
    action_type: str = "route"
    target_agent: str
    context: Dict[str, Any] = Field(default_factory=dict)


class GenerateResponse(AgentAction):
    """Generate a response to user"""
    action_type: str = "respond"
    content: str
    data: Optional[Dict[str, Any]] = None


# ============================================================================
# Knowledge Retrieval Models
# ============================================================================

class Document(BaseModel):
    """A document chunk from knowledge base"""
    id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None
    relevance_score: float = 0.0


# ============================================================================
# Response Models
# ============================================================================

class Response(BaseModel):
    """Response from the agent system to user (text and code only, no figures)"""
    type: Literal["plan", "success", "error", "clarification", "info"]
    content: str
    code: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    questions: Optional[List[Question]] = None
    suggestions: List[str] = Field(default_factory=list)
    awaiting_confirmation: bool = False


# ============================================================================
# Evaluation Models
# ============================================================================

class EvaluationReport(BaseModel):
    """Comprehensive evaluation of agent performance"""
    code_quality_score: float
    visual_quality_score: float
    spec_adherence_score: float
    conversation_efficiency: float
    error_recovery_rate: float
    overall_score: float
    details: Dict[str, Any] = Field(default_factory=dict)


# Forward reference resolution
WorkingMemory.model_rebuild()
