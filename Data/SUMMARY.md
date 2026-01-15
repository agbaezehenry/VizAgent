# Data Folder Summary

## Contents

### ✅ Generated Files

1. **omnitech_trends.csv** (36 rows)
   - Monthly revenue data for 3 categories over 12 months
   - Shows Cloud Service growth, stable Hardware, declining Consulting

2. **omnitech_satisfaction.csv** (5 rows)
   - Customer satisfaction scores by region
   - Highlights South region as underperformer

3. **omnitech_engagement.csv** (10 rows)
   - Employee engagement scores for 5 teams (2023 vs 2024)
   - Shows Engineering improvement, Support decline

4. **omnitech_marketing.csv** (20 rows)
   - Marketing campaign spend vs ROI data
   - Demonstrates ROI correlation with spend

### 📝 Python Scripts

1. **generate_data.py** - Creates all CSV files
2. **create_plots.py** - Generates before/after visualization comparisons
3. **README.md** - Full documentation

## Quick Start

```bash
# Generate data (already done!)
cd Data
python generate_data.py

# Create visualizations
python create_plots.py

# Use with Plotly Agent
cd ..
python web_app.py  # Then upload any CSV from Data folder
```

## Integration with Plotly Agent

These datasets are designed to work perfectly with the conversational agent:

```python
from plotly_agent.main import PlotlyAgent

# Initialize agent
agent = PlotlyAgent()

# Load data
agent.load_data("Data/omnitech_trends.csv")

# Chat naturally
response = agent.chat("Hello!")
# → "Hi! I'm here to help you create visualizations..."

# Request visualization
response = agent.chat("Show me revenue trends over time")
# → Agent generates Plotly code using reflection pattern

# Get the code
print(response['code'])
```

## Data Stories

Each dataset tells a specific business story:

### 1. Trends - Cloud Growth
**Story**: Cloud services are our growth engine, hardware is flat, consulting is declining
**Best viz**: Line chart with strategic color highlighting

### 2. Satisfaction - Regional Issues
**Story**: South region has significantly lower satisfaction scores
**Best viz**: Horizontal bar chart sorted by value with highlighting

### 3. Engagement - Team Changes
**Story**: Engineering improved dramatically, Support declined
**Best viz**: Slopegraph showing year-over-year changes

### 4. Marketing - Efficiency Analysis
**Story**: Identifying which campaigns deliver best ROI
**Best viz**: Scatterplot with quadrant analysis

## Visualization Best Practices Demonstrated

All example plots follow these principles:

1. **Strategic Color Use**
   - 1-2 colors maximum for highlights
   - Grey for context
   - Color conveys meaning (red=bad, green=good, blue=focus)

2. **Minimal Design**
   - Remove chart junk
   - Clean backgrounds
   - No unnecessary gridlines

3. **Direct Labeling**
   - Label data directly
   - Minimize or remove legends
   - Clear axis titles

4. **Sorted Data**
   - Sort by value to reveal patterns
   - Horizontal bars for easier reading
   - Logical ordering

5. **Context Addition**
   - Reference lines (averages)
   - Annotations for insights
   - Comparisons (before/after)

## Next Steps

1. **Test with Agent**: Upload CSV files via web interface
2. **Generate Code**: Ask agent to create various visualizations
3. **Compare**: Run create_plots.py to see before/after best practices
4. **Customize**: Modify generate_data.py to create your own datasets

## File Structure

```
Data/
├── README.md                      # Full documentation
├── SUMMARY.md                     # This file
├── generate_data.py               # Data generation script
├── create_plots.py                # Visualization examples
├── omnitech_trends.csv            # Monthly revenue data
├── omnitech_satisfaction.csv      # Regional satisfaction
├── omnitech_engagement.csv        # Employee engagement
└── omnitech_marketing.csv         # Marketing campaigns
```

## Requirements

All scripts use standard libraries:
- pandas
- numpy
- plotly

Already installed as part of the plotly_agent environment!
