"""
Example: Using OmniTech datasets with the Plotly Conversational Agent
Demonstrates the full conversational flow with real data.
"""

import sys
sys.path.append('..')  # Add parent directory to path

from plotly_agent.main import PlotlyAgent


def print_response(title: str, response: dict):
    """Pretty print agent response"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")
    print(f"\nAgent ({response['type']}): {response['content']}")

    if response.get('code'):
        print(f"\n--- Generated Code ---")
        print(response['code'])
        print("---")


def main():
    print("\n" + "="*70)
    print(" " * 15 + "OMNITECH DATA - AGENT DEMO")
    print("="*70)

    # Initialize agent
    print("\nInitializing Plotly Agent...")
    agent = PlotlyAgent()

    # Example 1: Greeting
    print("\n\n📍 Example 1: General Conversation")
    response = agent.chat("Hello! What can you help me with?")
    print_response("Greeting", response)

    # Example 2: Request without data
    print("\n\n📍 Example 2: Request Without Data")
    response = agent.chat("I want to visualize revenue trends")
    print_response("Request without data", response)

    # Load Trends Data
    print("\n\n📍 Loading Revenue Trends Data...")
    agent.load_data("omnitech_trends.csv")

    # Example 3: Now create visualization
    print("\n\n📍 Example 3: Create Line Chart")
    response = agent.chat("Show me revenue trends over time by category")
    print_response("Revenue trends visualization", response)

    # Example 4: Refinement
    print("\n\n📍 Example 4: Refinement Request")
    response = agent.chat("Highlight Cloud Service in a different color")
    print_response("Refinement", response)

    # Start new session with different data
    print("\n\n📍 Starting New Session with Satisfaction Data...")
    agent.new_session()
    agent.load_data("omnitech_satisfaction.csv")

    # Example 5: Bar chart
    print("\n\n📍 Example 5: Regional Comparison")
    response = agent.chat("Create a bar chart showing satisfaction scores by region")
    print_response("Satisfaction bar chart", response)

    # Example 6: Question about data
    print("\n\n📍 Example 6: Data Question")
    response = agent.chat("Which region has the lowest satisfaction?")
    print_response("Data question", response)

    # Session summary
    print("\n\n" + "="*70)
    print("  SESSION SUMMARY")
    print("="*70)
    summary = agent.get_session_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")

    print("\n✅ Demo complete!")
    print("\nTry these datasets:")
    print("  - omnitech_trends.csv (revenue over time)")
    print("  - omnitech_satisfaction.csv (regional scores)")
    print("  - omnitech_engagement.csv (team changes)")
    print("  - omnitech_marketing.csv (campaign ROI)")


if __name__ == "__main__":
    main()
