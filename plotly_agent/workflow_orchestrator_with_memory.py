"""
Workflow Orchestrator with Memory - Context-engineered visualization pipeline

Extends the base workflow orchestrator with long-term memory capabilities based on
OpenAI's Context Engineering pattern.

Pipeline:
User -> Communication Agent (with memory) -> Plot Generator -> Router -> Optimizer -> Verifier -> User
"""

import os
import tempfile
from typing import Dict, Any, Optional, List
from pathlib import Path
import pandas as pd
import traceback

from .workflow_agents import (
    CommunicationAgent,
    PlotGeneratorAgent,
    ChartRouter,
    LineOptimizerAgent,
    BarOptimizerAgent,
    ScatterOptimizerAgent,
    VerifierAgent
)

# Memory system imports
from .memory.memory_manager import PlotlyAgentState, add_visualization_to_history
from .memory.memory_tools import MemoryToolRegistry
from .memory.memory_injection import (
    inject_memories_into_prompt,
    should_reinject_session_memories,
    create_reinjection_message
)
from .memory.context_trimmer import ConversationManager
from .memory.memory_consolidation import consolidate_session_memories
from .state_storage import StateStorageManager


class WorkflowOrchestratorWithMemory:
    """
    Orchestrates the complete visualization workflow with long-term memory.

    Features:
    - Persistent user state (profile + memories)
    - Automatic conversation trimming with context preservation
    - Session memory consolidation
    - Memory-aware agents
    """

    def __init__(self, user_id: str = "anonymous", enable_memory: bool = True):
        """
        Initialize orchestrator.

        Args:
            user_id: User identifier for state persistence
            enable_memory: Enable memory features (default: True)
        """
        self.user_id = user_id
        self.enable_memory = enable_memory

        # Initialize agents
        self.communication_agent = CommunicationAgent()
        self.generator_agent = PlotGeneratorAgent()
        self.verifier_agent = VerifierAgent()

        # Initialize optimizer agents
        self.optimizers = {
            'line': LineOptimizerAgent(),
            'bar': BarOptimizerAgent(),
            'scatter': ScatterOptimizerAgent()
        }

        # Memory system
        if self.enable_memory:
            self.storage_manager = StateStorageManager()
            self.state = self.storage_manager.load(user_id, create_if_missing=True)
            self.memory_tools = MemoryToolRegistry(self.state)
            self.conversation_manager = ConversationManager(self.state, auto_trim=True)
        else:
            self.state = None
            self.memory_tools = None
            self.conversation_manager = None

        # Session state
        self.conversation_history: List[Dict[str, str]] = []
        self.data_summary: Optional[Dict[str, Any]] = None
        self.uploaded_file_path: Optional[str] = None
        self.current_story: Optional[str] = None

    def load_data(self, file_path: str) -> Dict[str, Any]:
        """
        Load data file and create summary.

        Returns:
            dict with keys:
                - success: bool
                - message: status message
                - data_summary: dict with data info
        """
        try:
            # Read the file
            df = pd.read_csv(file_path)

            # Store file path
            self.uploaded_file_path = file_path

            # Create data summary
            self.data_summary = {
                'columns': df.columns.tolist(),
                'dtypes': df.dtypes.to_dict(),
                'shape': df.shape,
                'head': df.head(5).to_dict(),
                'describe': df.describe().to_dict() if len(df.select_dtypes(include='number').columns) > 0 else None
            }

            return {
                'success': True,
                'message': f"Data loaded successfully! {df.shape[0]} rows, {df.shape[1]} columns.",
                'data_summary': self.data_summary
            }

        except Exception as e:
            return {
                'success': False,
                'message': f"Error loading data: {str(e)}",
                'data_summary': None
            }

    def chat(self, user_message: str) -> Dict[str, Any]:
        """
        Process user message through the workflow with memory.

        Returns:
            dict with keys:
                - type: 'conversation' | 'needs_data' | 'clarify' | 'visualization' | 'error'
                - message: response message
                - code: generated code (if type == 'visualization')
                - metadata: additional info about the workflow
        """
        # Add user message to history (with automatic trimming if memory enabled)
        if self.enable_memory and self.conversation_manager:
            self.conversation_history = self.conversation_manager.add_message(
                self.conversation_history,
                'user',
                user_message
            )
        else:
            self.conversation_history.append({
                'role': 'user',
                'content': user_message
            })

        try:
            # Check if we need to reinject session memories (after trimming)
            if self.enable_memory and should_reinject_session_memories(self.state):
                reinjection_msg = create_reinjection_message(self.state)
                self.conversation_history.insert(-1, {
                    'role': 'system',
                    'content': reinjection_msg
                })

            # Step 1: Communication Agent decides what to do
            # If memory enabled, inject memories into the agent's context
            comm_response = self._call_communication_agent(user_message)

            action = comm_response['action']

            # Handle different actions
            if action == 'conversation':
                # Just chatting
                response = {
                    'type': 'conversation',
                    'message': comm_response['message'],
                    'code': None,
                    'metadata': {'action': action}
                }

            elif action == 'needs_data':
                # Need data upload
                response = {
                    'type': 'needs_data',
                    'message': comm_response['message'],
                    'code': None,
                    'metadata': {'action': action}
                }

            elif action == 'clarify':
                # Need clarification
                response = {
                    'type': 'clarify',
                    'message': comm_response['message'],
                    'code': None,
                    'metadata': {'action': action}
                }

            elif action == 'ready':
                # Ready to generate visualization
                story_summary = comm_response['story_summary']
                self.current_story = story_summary

                # Run the visualization pipeline
                viz_result = self._run_visualization_pipeline(story_summary)

                # Record in visualization history
                if self.enable_memory and viz_result['code']:
                    add_visualization_to_history(
                        self.state,
                        chart_type=viz_result['metadata'].get('chart_type', 'unknown'),
                        story_summary=story_summary,
                        code_snippet=viz_result['code'][:200],
                        success=True
                    )

                response = {
                    'type': 'visualization',
                    'message': viz_result['message'],
                    'code': viz_result['code'],
                    'metadata': viz_result['metadata']
                }

            else:
                # Unknown action
                response = {
                    'type': 'error',
                    'message': f"Unknown action: {action}",
                    'code': None,
                    'metadata': {'action': action}
                }

            # Add assistant response to history
            if self.enable_memory and self.conversation_manager:
                self.conversation_history = self.conversation_manager.add_message(
                    self.conversation_history,
                    'assistant',
                    response['message']
                )
            else:
                self.conversation_history.append({
                    'role': 'assistant',
                    'content': response['message']
                })

            # Save state after each interaction
            if self.enable_memory:
                self.storage_manager.save(self.state)

            return response

        except Exception as e:
            error_msg = f"Error in workflow: {str(e)}\n{traceback.format_exc()}"
            return {
                'type': 'error',
                'message': error_msg,
                'code': None,
                'metadata': {'error': str(e)}
            }

    def _call_communication_agent(self, user_message: str) -> Dict[str, Any]:
        """
        Call communication agent with memory context injected.

        Args:
            user_message: User's message

        Returns:
            Communication agent response
        """
        # For now, call the agent normally
        # In a full implementation, we would inject memories into the agent's prompt
        # This requires modifying the agent classes to accept memory context
        return self.communication_agent.chat(
            user_message=user_message,
            conversation_history=self.conversation_history,
            data_summary=self.data_summary
        )

    def _run_visualization_pipeline(self, story_summary: str) -> Dict[str, Any]:
        """
        Run the complete visualization pipeline:
        Generator -> Router -> Optimizer -> Verifier

        Returns:
            dict with keys:
                - message: explanation message
                - code: final code
                - metadata: workflow information
        """
        metadata = {
            'story_summary': story_summary,
            'steps': []
        }

        try:
            # Step 1: Generate base plot
            print("\n[WORKFLOW] Step 1: Generating base plot...")
            gen_result = self.generator_agent.generate(
                story_summary=story_summary,
                data_summary=self.data_summary,
                file_path=self.uploaded_file_path
            )

            if not gen_result['success']:
                return {
                    'message': "Failed to generate base plot.",
                    'code': None,
                    'metadata': metadata
                }

            chart_type = gen_result['chart_type']
            base_code = gen_result['code']

            metadata['chart_type'] = chart_type
            metadata['steps'].append({
                'step': 'generator',
                'chart_type': chart_type,
                'reasoning': gen_result['reasoning']
            })

            print(f"[WORKFLOW] Generated {chart_type} chart")

            # Step 2: Execute base code to get result
            print("[WORKFLOW] Step 2: Executing base plot...")
            base_exec_result = self._execute_code(base_code)
            metadata['steps'].append({
                'step': 'base_execution',
                'status': base_exec_result['status']
            })

            # Step 3: Route to appropriate optimizer
            print("[WORKFLOW] Step 3: Routing to optimizer...")
            optimizer_type = ChartRouter.route(chart_type)
            optimizer = self.optimizers[optimizer_type]

            metadata['steps'].append({
                'step': 'router',
                'optimizer_type': optimizer_type
            })

            print(f"[WORKFLOW] Routed to {optimizer_type} optimizer")

            # Step 4: Optimize the plot
            print("[WORKFLOW] Step 4: Optimizing plot...")
            opt_result = optimizer.optimize(
                story_summary=story_summary,
                base_code=base_code,
                execution_result=base_exec_result['result']
            )

            if not opt_result['success']:
                return {
                    'message': "Failed to optimize plot.",
                    'code': base_code,  # Return base code as fallback
                    'metadata': metadata
                }

            optimized_code = opt_result['code']

            metadata['steps'].append({
                'step': 'optimizer',
                'improvements': opt_result['improvements']
            })

            print("[WORKFLOW] Plot optimized")

            # Step 5: Execute optimized code
            print("[WORKFLOW] Step 5: Executing optimized plot...")
            opt_exec_result = self._execute_code(optimized_code)
            metadata['steps'].append({
                'step': 'optimized_execution',
                'status': opt_exec_result['status']
            })

            # Step 6: Verify final code
            print("[WORKFLOW] Step 6: Verifying final plot...")
            verify_result = self.verifier_agent.verify(
                story_summary=story_summary,
                optimized_code=optimized_code,
                execution_result=opt_exec_result['result']
            )

            if not verify_result['success']:
                return {
                    'message': "Failed to verify plot.",
                    'code': optimized_code,  # Return optimized code as fallback
                    'metadata': metadata
                }

            final_code = verify_result['final_code']
            status = verify_result['status']

            metadata['steps'].append({
                'step': 'verifier',
                'status': status,
                'explanation': verify_result['explanation']
            })

            print(f"[WORKFLOW] Verification: {status}")

            # Build response message
            if status == 'approved':
                message = f"""I've created your visualization! Here's what I did:

**Story**: {story_summary}

**Chart Type**: {chart_type.capitalize()}

**Optimizations Applied**:
{opt_result['improvements']}

**Verification**: {verify_result['explanation']}

The code is ready to use!"""
            else:
                message = f"""I've created your visualization with some corrections.

**Story**: {story_summary}

**Chart Type**: {chart_type.capitalize()}

**Corrections Made**:
{verify_result['explanation']}

The code has been verified and is ready to use!"""

            return {
                'message': message,
                'code': final_code,
                'metadata': metadata
            }

        except Exception as e:
            error_msg = f"Error in visualization pipeline: {str(e)}\n{traceback.format_exc()}"
            print(f"[WORKFLOW] ERROR: {error_msg}")
            return {
                'message': error_msg,
                'code': None,
                'metadata': metadata
            }

    def _execute_code(self, code: str) -> Dict[str, str]:
        """
        Execute code and capture result.

        Returns:
            dict with keys:
                - status: 'success' | 'error'
                - result: stdout/stderr output
        """
        try:
            # Create temporary file for execution
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name

            # Execute the code (in a real system, use proper sandboxing)
            import subprocess
            result = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=30
            )

            # Clean up
            os.unlink(temp_file)

            if result.returncode == 0:
                return {
                    'status': 'success',
                    'result': result.stdout or 'Code executed successfully'
                }
            else:
                return {
                    'status': 'error',
                    'result': result.stderr or 'Unknown error'
                }

        except Exception as e:
            return {
                'status': 'error',
                'result': str(e)
            }

    def new_session(self, consolidate_memories: bool = True):
        """
        Start a new session.

        Args:
            consolidate_memories: If True, merge session memories into global memories
        """
        # Consolidate memories if enabled
        if self.enable_memory and consolidate_memories:
            stats = consolidate_session_memories(self.state)
            print(f"[Memory] Consolidated memories: {stats['session_notes_added']} session notes, "
                  f"{stats['merged_count']} duplicates removed")

            # Save state after consolidation
            self.storage_manager.save(self.state)

        # Clear session data
        self.conversation_history = []
        self.current_story = None

    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session"""
        summary = {
            'user_id': self.user_id,
            'memory_enabled': self.enable_memory,
            'messages_count': len(self.conversation_history),
            'data_loaded': self.data_summary is not None,
            'current_story': self.current_story
        }

        if self.enable_memory:
            from .memory_manager import get_memory_summary
            memory_summary = get_memory_summary(self.state)
            summary.update(memory_summary)

        return summary

    def get_memory_tools(self) -> Optional[MemoryToolRegistry]:
        """Get memory tools registry for manual memory operations."""
        return self.memory_tools if self.enable_memory else None

    def save_state(self):
        """Manually save state to disk."""
        if self.enable_memory:
            return self.storage_manager.save(self.state)
        return False
