"""
Tool calling framework with Pydantic-based tool definitions.
Provides data analysis tools for agents.
Simplified version - validates syntax only, no code execution.
"""

import time
from typing import List, Dict, Any, Optional, Literal
import pandas as pd
from pydantic import BaseModel, Field

from .models import Tool, ToolCall, ToolResult


# ============================================================================
# Code Validation (no execution)
# ============================================================================

class CodeValidator:
    """
    Validates Python code syntax without executing it.
    """

    @staticmethod
    def validate_syntax(code: str) -> tuple[bool, Optional[str]]:
        """
        Check if code has valid Python syntax.

        Args:
            code: Python code to validate

        Returns:
            (is_valid, error_message)
        """
        try:
            compile(code, '<string>', 'exec')
            return True, None
        except SyntaxError as e:
            return False, f"Syntax error at line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    @staticmethod
    def check_safety(code: str) -> tuple[bool, Optional[str]]:
        """
        Basic safety checks for code.

        Args:
            code: Python code to check

        Returns:
            (is_safe, reason_if_unsafe)
        """
        dangerous_patterns = [
            'import os', 'import sys', 'import subprocess',
            '__import__', 'eval(', 'compile(',
            'open(', 'file(', 'input(', 'raw_input(',
        ]

        for pattern in dangerous_patterns:
            if pattern in code:
                return False, f"Unsafe pattern detected: {pattern}"

        return True, None


# ============================================================================
# Tool Parameter Models
# ============================================================================

class DataSummaryParams(BaseModel):
    """Parameters for data summary tool"""
    columns: Optional[List[str]] = None
    include_stats: bool = True


class ColumnSearchParams(BaseModel):
    """Parameters for column search tool"""
    query: str
    search_type: Literal["name", "type", "values"] = "name"


class DataAnalysisParams(BaseModel):
    """Parameters for automated data analysis"""
    analysis_type: Literal["correlation", "distribution", "outliers", "missing"] = "correlation"
    columns: Optional[List[str]] = None


class ValidateCodeParams(BaseModel):
    """Parameters for code validation"""
    code: str


# ============================================================================
# Tool Implementations
# ============================================================================

class DataAnalysisTools:
    """Tools for analyzing dataframes"""

    @staticmethod
    def data_summary(df: pd.DataFrame, params: DataSummaryParams) -> Dict[str, Any]:
        """Generate summary statistics for dataframe columns"""
        cols = params.columns if params.columns else df.columns.tolist()

        summary = {}
        for col in cols:
            if col not in df.columns:
                continue

            col_summary = {
                'dtype': str(df[col].dtype),
                'null_count': int(df[col].isna().sum()),
                'null_percentage': float(df[col].isna().sum() / len(df) * 100),
                'unique_count': int(df[col].nunique()),
            }

            # Add stats for numeric columns
            if params.include_stats and pd.api.types.is_numeric_dtype(df[col]):
                col_summary.update({
                    'mean': float(df[col].mean()) if not df[col].isna().all() else None,
                    'median': float(df[col].median()) if not df[col].isna().all() else None,
                    'std': float(df[col].std()) if not df[col].isna().all() else None,
                    'min': float(df[col].min()) if not df[col].isna().all() else None,
                    'max': float(df[col].max()) if not df[col].isna().all() else None,
                })

            # Sample values
            col_summary['sample_values'] = df[col].dropna().head(5).tolist()

            summary[col] = col_summary

        return {
            'shape': df.shape,
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'columns': summary
        }

    @staticmethod
    def column_search(df: pd.DataFrame, params: ColumnSearchParams) -> List[str]:
        """Search for columns by name, type, or sample values"""
        query = params.query.lower()
        results = []

        if params.search_type == "name":
            # Search column names
            results = [col for col in df.columns if query in col.lower()]

        elif params.search_type == "type":
            # Search by data type
            type_map = {
                'numeric': pd.api.types.is_numeric_dtype,
                'int': pd.api.types.is_integer_dtype,
                'float': pd.api.types.is_float_dtype,
                'string': pd.api.types.is_string_dtype,
                'object': lambda s: s.dtype == 'object',
                'datetime': pd.api.types.is_datetime64_any_dtype,
                'bool': pd.api.types.is_bool_dtype,
            }

            checker = type_map.get(query)
            if checker:
                results = [col for col in df.columns if checker(df[col])]

        elif params.search_type == "values":
            # Search in sample values
            for col in df.columns:
                sample = df[col].dropna().astype(str).head(100)
                if any(query in val.lower() for val in sample):
                    results.append(col)

        return results

    @staticmethod
    def analyze_data(df: pd.DataFrame, params: DataAnalysisParams) -> Dict[str, Any]:
        """Perform automated data analysis"""
        cols = params.columns if params.columns else df.select_dtypes(include=['number']).columns.tolist()

        if params.analysis_type == "correlation":
            # Correlation matrix for numeric columns
            numeric_df = df[cols].select_dtypes(include=['number'])
            if len(numeric_df.columns) < 2:
                return {"error": "Need at least 2 numeric columns for correlation"}

            corr_matrix = numeric_df.corr()
            # Find strong correlations
            strong_corr = []
            for i in range(len(corr_matrix.columns)):
                for j in range(i+1, len(corr_matrix.columns)):
                    corr_val = corr_matrix.iloc[i, j]
                    if abs(corr_val) > 0.7:
                        strong_corr.append({
                            'col1': corr_matrix.columns[i],
                            'col2': corr_matrix.columns[j],
                            'correlation': float(corr_val)
                        })

            return {
                'correlation_matrix': corr_matrix.to_dict(),
                'strong_correlations': strong_corr
            }

        elif params.analysis_type == "distribution":
            # Distribution statistics
            results = {}
            for col in cols:
                if pd.api.types.is_numeric_dtype(df[col]):
                    results[col] = {
                        'skewness': float(df[col].skew()),
                        'kurtosis': float(df[col].kurtosis()),
                        'quartiles': df[col].quantile([0.25, 0.5, 0.75]).to_dict()
                    }
            return results

        elif params.analysis_type == "outliers":
            # Detect outliers using IQR method
            results = {}
            for col in cols:
                if pd.api.types.is_numeric_dtype(df[col]):
                    Q1 = df[col].quantile(0.25)
                    Q3 = df[col].quantile(0.75)
                    IQR = Q3 - Q1
                    lower_bound = Q1 - 1.5 * IQR
                    upper_bound = Q3 + 1.5 * IQR

                    outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)][col]
                    results[col] = {
                        'outlier_count': len(outliers),
                        'lower_bound': float(lower_bound),
                        'upper_bound': float(upper_bound),
                        'outlier_percentage': float(len(outliers) / len(df) * 100)
                    }
            return results

        elif params.analysis_type == "missing":
            # Missing data analysis
            results = {}
            for col in cols:
                missing_count = df[col].isna().sum()
                if missing_count > 0:
                    results[col] = {
                        'missing_count': int(missing_count),
                        'missing_percentage': float(missing_count / len(df) * 100)
                    }
            return results

        return {}


# ============================================================================
# Tool Registry
# ============================================================================

class ToolRegistry:
    """Registry of all available tools"""

    def __init__(self, df: Optional[pd.DataFrame] = None):
        self.df = df
        self.data_tools = DataAnalysisTools()
        self.validator = CodeValidator()

        self.tools: Dict[str, Tool] = self._register_tools()

    def _register_tools(self) -> Dict[str, Tool]:
        """Register all tools with their schemas"""
        return {
            "data_summary": Tool(
                name="data_summary",
                description="Get summary statistics for dataframe columns including types, null counts, and sample values",
                parameters_schema=DataSummaryParams.schema(),
                function=lambda params: self.data_tools.data_summary(self.df, params)
            ),
            "column_search": Tool(
                name="column_search",
                description="Search for columns by name, data type, or sample values",
                parameters_schema=ColumnSearchParams.schema(),
                function=lambda params: self.data_tools.column_search(self.df, params)
            ),
            "analyze_data": Tool(
                name="analyze_data",
                description="Perform automated data analysis: correlation, distribution, outliers, or missing data",
                parameters_schema=DataAnalysisParams.schema(),
                function=lambda params: self.data_tools.analyze_data(self.df, params)
            ),
            "validate_code": Tool(
                name="validate_code",
                description="Validate Python code syntax without executing it",
                parameters_schema=ValidateCodeParams.schema(),
                function=lambda params: {
                    'syntax_valid': self.validator.validate_syntax(params.code),
                    'safety_check': self.validator.check_safety(params.code)
                }
            ),
        }

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get tool by name"""
        return self.tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools with their descriptions"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters_schema
            }
            for tool in self.tools.values()
        ]

    def execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute a tool call and return result"""
        tool = self.get_tool(tool_call.tool_name)

        if not tool:
            return ToolResult(
                tool_name=tool_call.tool_name,
                success=False,
                error=f"Tool '{tool_call.tool_name}' not found"
            )

        start_time = time.time()

        try:
            # Parse parameters using Pydantic model
            param_class = eval(tool.parameters_schema['title'])  # Get parameter class
            params = param_class(**tool_call.parameters)

            # Execute tool
            result = tool.function(params)

            return ToolResult(
                tool_name=tool_call.tool_name,
                success=True,
                result=result,
                execution_time=time.time() - start_time
            )

        except Exception as e:
            return ToolResult(
                tool_name=tool_call.tool_name,
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )

    def update_dataframe(self, df: pd.DataFrame) -> None:
        """Update the dataframe used by tools"""
        self.df = df
