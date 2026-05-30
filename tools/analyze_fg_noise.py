import json
import statistics

# Load FG estimates
fg = json.load(open('config/fg_daily_estimates.json'))
d11 = fg['estimates'].get('day_11', {})

# Show items with spam outliers (min <= 3, many samples)
print("Items with spam outliers (min=3, many samples):")
for name, data in sorted(d11.items()):
    if data['samples'] > 10 and data['min_fg'] <= 3:
        print(f"  {name:<30} n={data['samples']:>4} min={data['min_fg']:>6} max={data['max_fg']:>7} med={data['median_fg']:>7} avg={data['avg_fg']:>7}")

print()

# Now compute trimmed stats (remove bottom 10% and top 10%)
# We need the raw data for this - let's re-scrape
print("Need raw price data to compute trimmed stats...")
print("Current FG data has", len(d11), "items in day_11")
