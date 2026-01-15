# Visualization Examples - Before & After

This folder contains examples of what the Plotly Agent produces, showing the transformation from basic plots to polished, story-driven visualizations.

## Overview

The agent applies data storytelling best practices automatically:
- ✅ Strategic color use (1-2 highlights, grey for context)
- ✅ Direct labeling (minimal or no legends)
- ✅ Sorted data for clarity
- ✅ Minimal design (no chart junk)
- ✅ Clear annotations and insights

---

## Line Chart Example

### File: [image_line.png](image_line.png)

**Use Case**: Revenue Trends Over Time

#### Before (Left Side)
- Default multi-colored lines
- All categories compete for attention
- Legend required to understand data
- No clear focus or story

#### After (Right Side)
- **Cloud Service** highlighted in bold blue (the focus of the story)
- **Hardware & Consulting** shown in grey (context only)
- Direct labeling at line endpoints
- Variable line widths (Cloud=4px, others=2px)
- Clean, minimal design
- Clear title: "Revenue Trends: Focus on Cloud Growth"

**Best Practices Applied**:
1. Strategic color highlighting
2. Direct labeling (no legend)
3. Variable line widths for emphasis
4. Minimal gridlines
5. Insight-driven title

---

## Bar Chart Example

### File: [image_bar.png](image_bar.png)

**Use Case**: Regional Satisfaction Comparison

#### Before (Left Side)
- Vertical bars with rainbow colors
- Alphabetical order (no pattern visible)
- Colors distract rather than inform
- Hard to read labels

#### After (Right Side)
- **South region** highlighted in red (problem area)
- Other regions in grey (context)
- **Horizontal orientation** for easier reading
- **Sorted by value** (lowest to highest)
- Data labels directly on bars
- Minimal axis clutter
- Clear title: "Regional Satisfaction: Issues in the South"

**Best Practices Applied**:
1. Horizontal bars for readability
2. Sorted by value to reveal pattern
3. Strategic red highlighting for problem
4. Data labels on bars
5. Minimal design (removed axis labels)
6. Insight-driven title

---

## Advanced Charts Example

### File: [image_scatter.png](image_scatter.png)

This image contains two chart types:

### 1. Slopegraph (Top)

**Use Case**: Employee Engagement Changes (2023 vs 2024)

#### Before (Top Left)
- Cluttered grouped bar chart
- Hard to see individual changes
- Blue/orange colors don't convey meaning
- Difficult to compare teams

#### After (Top Right)
- Clean slopegraph showing 2023 → 2024 changes
- **Engineering** in green (improvement)
- **Support** in red (decline)
- Other teams in grey (stable)
- Direct labeling at both endpoints
- Easy to see who improved/declined
- Title: "Engagement Changes: 2023 vs 2024"

**Best Practices Applied**:
1. Right chart type (slopegraph for change)
2. Color conveys meaning (green=good, red=bad)
3. Direct labeling (no legend)
4. Shows individual team values
5. Minimal design

---

### 2. Scatter Plot (Bottom)

**Use Case**: Marketing Campaign Efficiency (Spend vs ROI)

#### Before (Bottom Left)
- Plain blue scatter points
- No context or insights
- Just raw data
- No clear story

#### After (Bottom Right)
- All campaigns in grey (context)
- **Most efficient campaign** highlighted in blue
- **Quadrant analysis** with dotted reference lines
  - Vertical line: Average spend
  - Horizontal line: Average ROI
- Annotation pointing to best performer
- Easy to identify high/low performers
- Title: "Marketing Efficiency: Quadrant Analysis"

**Best Practices Applied**:
1. Strategic highlighting (best performer)
2. Context lines (average spend/ROI)
3. Quadrant analysis for segmentation
4. Direct annotation
5. Color conveys focus

---

## How the Agent Works

The multi-agent pipeline creates these visualizations:

```
User Request
    ↓
Communication Agent (understands story)
    ↓
Plot Generator (creates base plot)
    ↓
Router (selects specialist)
    ↓
Optimizer Agent (applies best practices)
    ├─ LineOptimizer for trends
    ├─ BarOptimizer for comparisons
    └─ ScatterOptimizer for relationships
    ↓
Verifier (ensures quality)
    ↓
Final Optimized Code
```

## Key Transformations

### Color Strategy
- **Before**: Rainbow colors, all equal weight
- **After**: 1-2 strategic highlights, grey for context

### Labeling
- **Before**: Legends, axis labels, cluttered
- **After**: Direct labeling, minimal text, clear

### Chart Type
- **Before**: Generic bar/line charts
- **After**: Right chart for the story (including slopegraphs, etc.)

### Focus
- **Before**: Show all data equally
- **After**: Tell a specific story with clear insights

### Design
- **Before**: Default themes, gridlines, borders
- **After**: Minimal design, no chart junk

## Usage

These examples demonstrate what you'll get when you use the agent:

```python
from plotly_agent.workflow_orchestrator import WorkflowOrchestrator

orch = WorkflowOrchestrator()
orch.load_data('Data/omnitech_trends.csv')

# Line chart example
response = orch.chat("Show me revenue trends, highlighting Cloud Service")

# Bar chart example
orch.load_data('Data/omnitech_satisfaction.csv')
response = orch.chat("Compare regions, highlight the problem area")

# Scatter plot example
orch.load_data('Data/omnitech_marketing.csv')
response = orch.chat("Show campaign efficiency with quadrant analysis")
```

## Best Practice Principles

All examples follow these data storytelling principles:

1. **Highlight What Matters**
   - Use color strategically (1-2 colors max)
   - Everything else in grey for context

2. **Remove Chart Junk**
   - Minimal gridlines (or none)
   - No unnecessary borders or backgrounds
   - Clean, simple design

3. **Direct Labeling**
   - Label data directly on the chart
   - Minimize or remove legends
   - Clear, readable text

4. **Sort Meaningfully**
   - Order data to reveal patterns
   - Use horizontal bars for easier reading
   - Logical sequencing

5. **Add Context**
   - Reference lines (averages, targets)
   - Annotations for key insights
   - Comparisons (before/after, benchmarks)

6. **Choose Right Chart**
   - Line for trends over time
   - Bar for comparisons
   - Scatter for relationships
   - Slopegraph for changes
   - Match visualization to story

## Learn More

- **Get Started**: [WORKFLOW_QUICKSTART.md](../WORKFLOW_QUICKSTART.md)
- **Full Documentation**: [WORKFLOW_ARCHITECTURE.md](../WORKFLOW_ARCHITECTURE.md)
- **Sample Data**: [Data/](../Data/)
- **Example Code**: [workflow_example.py](../workflow_example.py)

---

**Note**: These are actual outputs from the agent using the sample datasets in the `Data/` folder. The transformations are applied automatically by the specialized optimizer agents!
