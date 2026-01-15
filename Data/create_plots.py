"""
Create advanced Plotly visualizations with before/after comparisons.
Demonstrates best practices for storytelling with data.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd

# Load Data
df_trends = pd.read_csv('omnitech_trends.csv')
df_sat = pd.read_csv('omnitech_satisfaction.csv')
df_slope = pd.read_csv('omnitech_engagement.csv')
df_scatter = pd.read_csv('omnitech_marketing.csv')

# Helper to configure standard 'After' layout
def clean_layout(fig, title):
    fig.update_layout(
        title_text=title,
        template="simple_white",
        width=900,  # Reduced width as requested
        height=500,
        showlegend=False
    )

# ==========================================
# 1. LINE CHART (Trends)
# ==========================================
print("Creating Line Chart: Revenue Trends...")
fig_line = make_subplots(rows=1, cols=2, subplot_titles=("Before: Default", "After: Strategic Focus"))

# -- Before --
for cat in df_trends['Category'].unique():
    d = df_trends[df_trends['Category'] == cat]
    fig_line.add_trace(go.Scatter(x=d['Date'], y=d['Revenue'], mode='lines', name=cat), row=1, col=1)

# -- After --
# Highlight 'Cloud Service' in Blue, others in Grey
colors = {'Cloud Service': '#1F77B4', 'Hardware': '#D3D3D3', 'Consulting': '#D3D3D3'}
widths = {'Cloud Service': 4, 'Hardware': 2, 'Consulting': 2}

for cat in df_trends['Category'].unique():
    d = df_trends[df_trends['Category'] == cat]
    fig_line.add_trace(go.Scatter(
        x=d['Date'], y=d['Revenue'], mode='lines',
        line=dict(color=colors[cat], width=widths[cat]),
        name=cat, showlegend=False
    ), row=1, col=2)

    # Direct Labeling (Last Point)
    last_pt = d.iloc[-1]
    fig_line.add_annotation(
        x=last_pt['Date'], y=last_pt['Revenue'], text=cat,
        showarrow=False, xanchor="left", font=dict(color=colors[cat], size=10),
        row=1, col=2
    )

clean_layout(fig_line, "Revenue Trends: Focus on Cloud Growth")
fig_line.show()


# ==========================================
# 2. BAR CHART (Satisfaction)
# ==========================================
print("Creating Bar Chart: Regional Satisfaction...")
fig_bar = make_subplots(rows=1, cols=2, subplot_titles=("Before: Rainbow Soup", "After: Highlighted Story"))

# -- Before --
fig_bar.add_trace(go.Bar(x=df_sat['Region'], y=df_sat['Satisfaction_Score'], marker_color=px.colors.qualitative.Plotly), row=1, col=1)

# -- After --
# Sort and Highlight South
df_sat_sorted = df_sat.sort_values('Satisfaction_Score', ascending=True)
colors_bar = ['#D9534F' if r == 'South' else '#D3D3D3' for r in df_sat_sorted['Region']]

fig_bar.add_trace(go.Bar(
    x=df_sat_sorted['Satisfaction_Score'], y=df_sat_sorted['Region'], orientation='h',
    marker_color=colors_bar, text=df_sat_sorted['Satisfaction_Score'], textposition='auto'
), row=1, col=2)

clean_layout(fig_bar, "Regional Satisfaction: Issues in the South")
fig_bar.update_xaxes(showticklabels=False, row=1, col=2)  # Remove axis noise
fig_bar.show()


# ==========================================
# 3. SLOPEGRAPH (Engagement)
# ==========================================
print("Creating Slopegraph: Engagement Changes...")
fig_slope = make_subplots(rows=1, cols=2, subplot_titles=("Before: Cluttered Bars", "After: Slopegraph"))

# -- Before (Grouped Bar) --
# We manually create bar traces for before
d2023 = df_slope[df_slope['Year'] == 2023]
d2024 = df_slope[df_slope['Year'] == 2024]
fig_slope.add_trace(go.Bar(x=d2023['Team'], y=d2023['Engagement_Score'], name='2023'), row=1, col=1)
fig_slope.add_trace(go.Bar(x=d2024['Team'], y=d2024['Engagement_Score'], name='2024'), row=1, col=1)

# -- After (Slope) --
for team in df_slope['Team'].unique():
    d = df_slope[df_slope['Team'] == team]
    # Color logic
    color = '#D3D3D3'
    if team == 'Engineering':
        color = '#2CA02C'  # Good
    if team == 'Support':
        color = '#D62728'  # Bad

    fig_slope.add_trace(go.Scatter(
        x=d['Year'], y=d['Engagement_Score'], mode='lines+markers',
        line=dict(color=color), showlegend=False,
        marker=dict(size=8)
    ), row=1, col=2)

    # Labels
    y_start = d[d['Year'] == 2023]['Engagement_Score'].values[0]
    y_end = d[d['Year'] == 2024]['Engagement_Score'].values[0]
    fig_slope.add_annotation(x=2023, y=y_start, text=f"{team} {y_start}", showarrow=False, xanchor="right", xshift=-5, row=1, col=2)
    fig_slope.add_annotation(x=2024, y=y_end, text=f"{y_end}", showarrow=False, xanchor="left", xshift=5, row=1, col=2)

clean_layout(fig_slope, "Engagement Changes: 2023 vs 2024")
fig_slope.update_xaxes(tickvals=[2023, 2024], range=[2022.5, 2024.5], row=1, col=2)
fig_slope.update_yaxes(showgrid=False, showticklabels=False, row=1, col=2)
fig_slope.show()


# ==========================================
# 4. SCATTERPLOT (Marketing)
# ==========================================
print("Creating Scatterplot: Marketing Efficiency...")
fig_scatter = make_subplots(rows=1, cols=2, subplot_titles=("Before: Just Data", "After: Context Added"))

# -- Before --
fig_scatter.add_trace(go.Scatter(x=df_scatter['Spend'], y=df_scatter['ROI'], mode='markers'), row=1, col=1)

# -- After --
# Add averages and highlight best
avg_roi = df_scatter['ROI'].mean()
avg_spend = df_scatter['Spend'].mean()
best_camp = df_scatter.loc[df_scatter['ROI'].idxmax()]

fig_scatter.add_trace(go.Scatter(
    x=df_scatter['Spend'], y=df_scatter['ROI'], mode='markers',
    marker=dict(color='#D3D3D3'), showlegend=False
), row=1, col=2)

# Highlight Best
fig_scatter.add_trace(go.Scatter(
    x=[best_camp['Spend']], y=[best_camp['ROI']], mode='markers',
    marker=dict(color='#1F77B4', size=12), showlegend=False
), row=1, col=2)

# Add Quadrant Lines (Shapes)
fig_scatter.add_shape(type="line", x0=avg_spend, y0=df_scatter['ROI'].min(), x1=avg_spend, y1=df_scatter['ROI'].max(),
                      line=dict(color="grey", width=1, dash="dot"), row=1, col=2)
fig_scatter.add_shape(type="line", x0=df_scatter['Spend'].min(), y0=avg_roi, x1=df_scatter['Spend'].max(), y1=avg_roi,
                      line=dict(color="grey", width=1, dash="dot"), row=1, col=2)

fig_scatter.add_annotation(x=best_camp['Spend'], y=best_camp['ROI'], text="Most Efficient", ay=-30, row=1, col=2)

clean_layout(fig_scatter, "Marketing Efficiency: Quadrant Analysis")
fig_scatter.show()

print("\n✅ All visualizations created successfully!")
