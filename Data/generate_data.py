"""
Generate sample datasets for OmniTech visualization examples.
Creates 4 CSV files demonstrating different business scenarios.
"""

import pandas as pd
import numpy as np

# Set random seed for reproducibility
np.random.seed(42)

# --- 1. Monthly Trends (for Line & Stacked Bar) ---
dates = pd.date_range(start='2024-01-01', periods=12, freq='ME')  # ME = Month End (M is deprecated)
data_trends = []
for date in dates:
    # Story: Cloud grows, Hardware is flat, Consulting declines
    base_cloud = 100 + (date.month * 15) + np.random.randint(-10, 10)
    base_hw = 150 + np.random.randint(-20, 20)
    base_consult = 200 - (date.month * 10) + np.random.randint(-10, 10)
    data_trends.append([date, 'Cloud Service', base_cloud])
    data_trends.append([date, 'Hardware', base_hw])
    data_trends.append([date, 'Consulting', base_consult])
df_trends = pd.DataFrame(data_trends, columns=['Date', 'Category', 'Revenue'])
df_trends.to_csv('omnitech_trends.csv', index=False)
print(f"[OK] Created omnitech_trends.csv ({len(df_trends)} rows)")

# --- 2. Regional Satisfaction (for Bar Chart) ---
regions = ['North', 'South', 'East', 'West', 'Central']
data_sat = []
for region in regions:
    score = np.random.randint(60, 95)
    # Story: South is the underperformer
    if region == 'South':
        score -= 25
    data_sat.append([region, score])
df_sat = pd.DataFrame(data_sat, columns=['Region', 'Satisfaction_Score'])
df_sat.to_csv('omnitech_satisfaction.csv', index=False)
print(f"[OK] Created omnitech_satisfaction.csv ({len(df_sat)} rows)")

# --- 3. Employee Engagement (for Slopegraph) ---
teams = ['Sales', 'Engineering', 'HR', 'Marketing', 'Support']
data_slope = []
for team in teams:
    score_2023 = np.random.randint(55, 75)
    # Story: Engineering improved, Support dropped
    change = np.random.randint(-5, 5)
    if team == 'Engineering':
        change = 15
    if team == 'Support':
        change = -15
    score_2024 = score_2023 + change
    data_slope.append([team, 2023, score_2023])
    data_slope.append([team, 2024, score_2024])
df_slope = pd.DataFrame(data_slope, columns=['Team', 'Year', 'Engagement_Score'])
df_slope.to_csv('omnitech_engagement.csv', index=False)
print(f"[OK] Created omnitech_engagement.csv ({len(df_slope)} rows)")

# --- 4. Marketing ROI (for Scatterplot) ---
campaigns = [f'Camp_{i}' for i in range(1, 21)]
data_scatter = []
for c in campaigns:
    spend = np.random.randint(1000, 10000)
    # Story: ROI is generally correlated, but with noise
    roi = (spend * 0.05) + np.random.randint(-100, 100)
    data_scatter.append([c, spend, roi])
df_scatter = pd.DataFrame(data_scatter, columns=['Campaign', 'Spend', 'ROI'])
df_scatter.to_csv('omnitech_marketing.csv', index=False)
print(f"[OK] Created omnitech_marketing.csv ({len(df_scatter)} rows)")

print("\n[SUCCESS] Data generation complete!")
print("Files created:")
print("  - omnitech_trends.csv")
print("  - omnitech_satisfaction.csv")
print("  - omnitech_engagement.csv")
print("  - omnitech_marketing.csv")
