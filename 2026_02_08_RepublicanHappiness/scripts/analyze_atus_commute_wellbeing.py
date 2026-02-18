import pandas as pd
import gzip
import matplotlib.pyplot as plt
import numpy as np

# Read ATUS data
print("Reading ATUS data...")
with gzip.open('atus_00002.csv.gz', 'rt') as f:
    df = pd.read_csv(f)

# Activity codes for commuting
commute_codes = [180501, 180502]

# Filter for commute activities
commute_df = df[df['ACTIVITY'].isin(commute_codes)].copy()

# Filter out non-metropolitan areas and records without wellbeing data
# Wellbeing scores of 99 indicate "not applicable" or missing
commute_df = commute_df[commute_df['METAREA'] > 0]
commute_df = commute_df[
    (commute_df['SCHAPPY'] != 99) & 
    (commute_df['SCSTRESS'] != 99) & 
    (commute_df['SCSAD'] != 99) & 
    (commute_df['SCPAIN'] != 99) & 
    (commute_df['SCTIRED'] != 99)
]

print(f"Commute records with wellbeing data: {len(commute_df):,}")

# Map METAREA codes to names
metro_names = {
    521: "Atlanta",
    1122: "Boston",
    1601: "Charlotte",
    1681: "Cincinnati", 
    1921: "Chicago",
    2081: "Cleveland",
    2161: "Columbus",
    2310: "Dallas",
    3660: "Houston",
    4481: "Los Angeles",
    5000: "Miami",
    5081: "Milwaukee",
    5601: "Minneapolis",
    5960: "Phoenix",
    6161: "Philadelphia",
    6400: "Pittsburgh",
    6640: "San Diego",
    7160: "St. Louis",
    7360: "San Jose",
    7601: "Seattle",
    8841: "Washington DC"
}

# Add metro names
commute_df['metro_name'] = commute_df['METAREA'].map(metro_names)

# Filter for metros with names
commute_df = commute_df[commute_df['metro_name'].notna()]

print(f"Records in named metros: {len(commute_df):,}")

# Calculate weighted average wellbeing scores by metro
metro_wellbeing = []

for metro_code, metro_name in metro_names.items():
    metro_data = commute_df[commute_df['METAREA'] == metro_code]
    
    if len(metro_data) >= 5:  # Only include metros with at least 5 observations
        # Calculate weighted means
        total_weight = metro_data['WT06'].sum()
        
        weighted_happy = (metro_data['SCHAPPY'] * metro_data['WT06']).sum() / total_weight
        weighted_stress = (metro_data['SCSTRESS'] * metro_data['WT06']).sum() / total_weight
        weighted_sad = (metro_data['SCSAD'] * metro_data['WT06']).sum() / total_weight
        weighted_pain = (metro_data['SCPAIN'] * metro_data['WT06']).sum() / total_weight
        weighted_tired = (metro_data['SCTIRED'] * metro_data['WT06']).sum() / total_weight
        
        # Calculate average commute duration for context
        weighted_duration = (metro_data['DURATION'] * metro_data['WT06']).sum() / total_weight
        
        metro_wellbeing.append({
            'metro': metro_name,
            'happiness': weighted_happy,
            'stress': weighted_stress,
            'sadness': weighted_sad,
            'pain': weighted_pain,
            'tiredness': weighted_tired,
            'avg_duration': weighted_duration,
            'n_obs': len(metro_data),
            'total_weight': total_weight
        })

# Convert to DataFrame
wellbeing_df = pd.DataFrame(metro_wellbeing)
wellbeing_df = wellbeing_df.sort_values('stress', ascending=False)

print(f"\nMetros with sufficient wellbeing data: {len(wellbeing_df)}")

# Print Atlanta's stats if available
atlanta_data = wellbeing_df[wellbeing_df['metro'] == 'Atlanta']
if len(atlanta_data) > 0:
    print("\nAtlanta commute wellbeing scores (0-6 scale):")
    print(f"  Happiness: {atlanta_data['happiness'].values[0]:.2f}")
    print(f"  Stress: {atlanta_data['stress'].values[0]:.2f}")
    print(f"  Sadness: {atlanta_data['sadness'].values[0]:.2f}")
    print(f"  Pain: {atlanta_data['pain'].values[0]:.2f}")
    print(f"  Tiredness: {atlanta_data['tiredness'].values[0]:.2f}")
    print(f"  Sample size: {atlanta_data['n_obs'].values[0]}")

# Create visualization
if len(wellbeing_df) > 0:
    # Create figure with multiple subplots
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle('Commuter Well-being During Commutes by City (ATUS 2021)\nScale: 0 (not at all) to 6 (very)', fontsize=16)
    
    emotions = [
        ('stress', 'Stress Level', axes[0, 0], 'Reds'),
        ('happiness', 'Happiness Level', axes[0, 1], 'Blues_r'),
        ('tiredness', 'Tiredness Level', axes[0, 2], 'Oranges'),
        ('sadness', 'Sadness Level', axes[1, 0], 'Purples'),
        ('pain', 'Pain Level', axes[1, 1], 'YlOrRd'),
    ]
    
    for emotion, title, ax, cmap in emotions:
        # Sort by this emotion
        sorted_df = wellbeing_df.sort_values(emotion, ascending=True)
        
        metros = sorted_df['metro'].values
        values = sorted_df[emotion].values
        
        # Color Atlanta differently
        colors = ['red' if m == 'Atlanta' else 'gray' for m in metros]
        
        y_pos = np.arange(len(metros))
        bars = ax.barh(y_pos, values)
        
        # Set bar colors
        for bar, color in zip(bars, colors):
            bar.set_color(color)
        
        # Add value labels
        for i, (metro, val) in enumerate(zip(metros, values)):
            ax.text(val + 0.05, i, f'{val:.2f}', va='center', fontsize=9)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(metros, fontsize=10)
        ax.set_xlabel('Score (0-6)')
        ax.set_title(title, fontsize=12)
        ax.set_xlim(0, 6)
        ax.grid(axis='x', alpha=0.3)
    
    # Use the last subplot for a comparison table
    ax_table = axes[1, 2]
    ax_table.axis('off')
    
    # Create comparison text
    if len(atlanta_data) > 0:
        atlanta_rank_stress = len(wellbeing_df) - wellbeing_df[wellbeing_df['metro'] == 'Atlanta'].index[0]
        atlanta_rank_happy = len(wellbeing_df) - wellbeing_df.sort_values('happiness', ascending=False)[wellbeing_df.sort_values('happiness', ascending=False)['metro'] == 'Atlanta'].index[0]
        
        comparison_text = f"Atlanta Rankings (out of {len(wellbeing_df)} metros):\n\n"
        comparison_text += f"Stress: #{atlanta_rank_stress} (higher rank = more stressed)\n"
        comparison_text += f"Happiness: #{atlanta_rank_happy} (higher rank = happier)\n\n"
        comparison_text += f"Atlanta avg commute: {atlanta_data['avg_duration'].values[0]:.1f} min\n"
        comparison_text += f"Sample size: {atlanta_data['n_obs'].values[0]} commutes"
        
        ax_table.text(0.1, 0.5, comparison_text, fontsize=12, 
                     transform=ax_table.transAxes, verticalalignment='center')
    
    plt.tight_layout()
    plt.savefig('atus_commute_wellbeing.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # Print summary statistics
    print("\n=== WELLBEING DURING COMMUTES BY METRO ===")
    print("\nMost stressed commuters:")
    for _, row in wellbeing_df.head(5).iterrows():
        print(f"  {row['metro']}: {row['stress']:.2f} (n={row['n_obs']})")
    
    print("\nLeast stressed commuters:")
    for _, row in wellbeing_df.tail(5).iterrows():
        print(f"  {row['metro']}: {row['stress']:.2f} (n={row['n_obs']})")
    
    print("\nHappiest commuters:")
    happy_sorted = wellbeing_df.sort_values('happiness', ascending=False)
    for _, row in happy_sorted.head(5).iterrows():
        print(f"  {row['metro']}: {row['happiness']:.2f} (n={row['n_obs']})")
    
    # Create correlation matrix
    plt.figure(figsize=(8, 6))
    emotions_cols = ['happiness', 'stress', 'sadness', 'pain', 'tiredness']
    corr_matrix = wellbeing_df[emotions_cols].corr()
    
    # Simple heatmap without seaborn
    im = plt.imshow(corr_matrix, cmap='coolwarm', aspect='auto', vmin=-1, vmax=1)
    plt.colorbar(im)
    
    # Add labels
    plt.xticks(range(len(emotions_cols)), emotions_cols, rotation=45)
    plt.yticks(range(len(emotions_cols)), emotions_cols)
    
    # Add correlation values as text
    for i in range(len(emotions_cols)):
        for j in range(len(emotions_cols)):
            plt.text(j, i, f'{corr_matrix.iloc[i, j]:.2f}', 
                    ha='center', va='center',
                    color='white' if abs(corr_matrix.iloc[i, j]) > 0.5 else 'black')
    
    plt.title('Correlation Between Emotions During Commutes')
    plt.tight_layout()
    plt.savefig('atus_commute_emotions_correlation.png', dpi=300, bbox_inches='tight')
    plt.show()
    
else:
    print("\nInsufficient wellbeing data for visualization")