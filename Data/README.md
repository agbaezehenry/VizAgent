# OmniTech Data Assets

This folder contains sample datasets and visualization scripts for demonstrating advanced Plotly visualizations.

## Files

### Data Generation
- **generate_data.py** - Creates 4 sample CSV files with realistic business scenarios

### Visualization
- **create_plots.py** - Creates before/after comparison visualizations demonstrating best practices

### Generated CSV Files
After running `generate_data.py`, you'll have:

1. **omnitech_trends.csv** - Monthly revenue trends by category
   - Columns: Date, Category, Revenue
   - Story: Cloud services growing, consulting declining

2. **omnitech_satisfaction.csv** - Regional customer satisfaction scores
   - Columns: Region, Satisfaction_Score
   - Story: South region underperforming

3. **omnitech_engagement.csv** - Employee engagement changes (2023 vs 2024)
   - Columns: Team, Year, Engagement_Score
   - Story: Engineering improved, Support declined

4. **omnitech_marketing.csv** - Marketing campaign spend vs ROI
   - Columns: Campaign, Spend, ROI
   - Story: Identifying most efficient campaigns

## Usage

### Generate Data
```bash
cd Data
python generate_data.py
```

### Create Visualizations
```bash
python create_plots.py
```

### Use with Plotly Agent
```python
from plotly_agent.main import PlotlyAgent

agent = PlotlyAgent()
agent.load_data("Data/omnitech_trends.csv")
response = agent.chat("Create a line chart showing revenue trends")
print(response['code'])
```

## Visualization Techniques Demonstrated

### 1. Line Chart - Revenue Trends
**Before**: Standard multi-line chart with default colors
**After**: Strategic focus with:
- Blue highlight on key metric (Cloud Service)
- Grey for context (Hardware, Consulting)
- Direct labeling instead of legend
- Variable line widths for emphasis

### 2. Bar Chart - Regional Satisfaction
**Before**: Vertical bars with rainbow colors
**After**: Improved storytelling with:
- Horizontal orientation for easier reading
- Sorted by value
- Red highlight on problem area (South)
- Grey for context
- Data labels on bars
- Minimal axis noise

### 3. Slopegraph - Engagement Changes
**Before**: Cluttered grouped bar chart
**After**: Clean slopegraph with:
- Lines connecting 2023 to 2024
- Green for improvements (Engineering)
- Red for declines (Support)
- Grey for stable teams
- Direct labeling on endpoints

### 4. Scatterplot - Marketing Efficiency
**Before**: Plain scatter without context
**After**: Quadrant analysis with:
- Dotted lines for averages (spend/ROI)
- Blue highlight on best performer
- Grey for all campaigns
- Annotation on key insight
- Four quadrants for strategic grouping

## Design Principles

These visualizations demonstrate key data storytelling principles:

1. **Highlight what matters** - Use color strategically (1-2 colors max)
2. **Remove chart junk** - Minimize gridlines, legends, unnecessary labels
3. **Direct labeling** - Label data points directly instead of using legends
4. **Sort meaningfully** - Order data to reveal patterns
5. **Add context** - Reference lines, annotations, comparisons
6. **Choose right chart** - Match visualization type to the story

## Requirements

```bash
pip install plotly pandas numpy
```
