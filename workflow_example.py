"""
Example: Using the new workflow architecture with Plotly Agent

Demonstrates:
- Natural conversation
- Data upload
- Story-driven visualization
- Multi-agent pipeline
"""

import sys
from plotly_agent.workflow_orchestrator import WorkflowOrchestrator


def print_separator(title=""):
    """Print a nice separator"""
    print("\n" + "="*70)
    if title:
        print(f"  {title}")
        print("="*70)
    print()


def print_response(response: dict):
    """Pretty print workflow response"""
    print(f"Type: {response['type']}")
    print(f"\nMessage:\n{response['message']}")

    if response.get('code'):
        print(f"\n--- Generated Code ---")
        print(response['code'])
        print("---")

    if response.get('metadata'):
        print(f"\n--- Workflow Metadata ---")
        metadata = response['metadata']

        if 'story_summary' in metadata:
            print(f"Story: {metadata['story_summary']}")

        if 'steps' in metadata:
            print(f"\nPipeline Steps:")
            for step in metadata['steps']:
                step_name = step.get('step', 'unknown')
                print(f"  • {step_name.capitalize()}")

                # Show key info from each step
                if step_name == 'generator':
                    print(f"    Chart Type: {step.get('chart_type')}")
                    print(f"    Reasoning: {step.get('reasoning')}")

                elif step_name == 'router':
                    print(f"    Optimizer: {step.get('optimizer_type')}")

                elif step_name == 'optimizer':
                    improvements = step.get('improvements', '')
                    if improvements:
                        # Show first line of improvements
                        first_line = improvements.split('\n')[0]
                        print(f"    Improvements: {first_line}...")

                elif step_name == 'verifier':
                    print(f"    Status: {step.get('status')}")


def main():
    print_separator("PLOTLY AGENT - NEW WORKFLOW DEMO")

    print("Initializing Workflow Orchestrator...")
    orchestrator = WorkflowOrchestrator()

    # Example 1: Greeting (no data)
    print_separator("Example 1: Initial Greeting")
    response = orchestrator.chat("Hello! What can you help me with?")
    print_response(response)

    # Example 2: Request without data
    print_separator("Example 2: Request Without Data")
    response = orchestrator.chat("I want to visualize revenue trends")
    print_response(response)

    # Load data
    print_separator("Loading Data")
    print("Loading Data/omnitech_trends.csv...")
    load_result = orchestrator.load_data("Data/omnitech_trends.csv")
    print(f"Status: {load_result['message']}")

    # Example 3: Now create visualization
    print_separator("Example 3: Create Line Chart")
    response = orchestrator.chat(
        "Show me revenue trends over time by category, highlighting Cloud Service"
    )
    print_response(response)

    # Example 4: Start new data session
    print_separator("Example 4: New Session - Bar Chart")
    orchestrator.new_session()
    orchestrator.load_data("Data/omnitech_satisfaction.csv")

    response = orchestrator.chat(
        "Create a bar chart showing satisfaction scores by region, "
        "highlighting which region has the lowest score"
    )
    print_response(response)

    # Example 5: Scatter plot
    print_separator("Example 5: New Session - Scatter Plot")
    orchestrator.new_session()
    orchestrator.load_data("Data/omnitech_marketing.csv")

    response = orchestrator.chat(
        "Show me the relationship between campaign spend and ROI, "
        "and highlight the most efficient campaigns"
    )
    print_response(response)

    # Session summary
    print_separator("Session Summary")
    summary = orchestrator.get_session_summary()
    print(f"Messages exchanged: {summary['messages_count']}")
    print(f"Data loaded: {summary['data_loaded']}")
    print(f"Current story: {summary['current_story']}")

    print_separator()
    print("✅ Demo complete!")
    print("\nKey Features Demonstrated:")
    print("  • Natural conversation flow")
    print("  • Automatic data checking")
    print("  • Story-driven visualization")
    print("  • Multi-agent pipeline (Communication → Generator → Router → Optimizer → Verifier)")
    print("  • Chart-type specialization (Line, Bar, Scatter)")
    print("  • Automatic best practices application")
    print("  • Code verification")
    print()


if __name__ == "__main__":
    main()
