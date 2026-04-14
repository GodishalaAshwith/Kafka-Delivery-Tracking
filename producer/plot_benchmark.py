import matplotlib.pyplot as plt

# Data from our benchmarking run
riders = ['10', '100', '1000', '10000']
throughput = [9.94, 99.23, 883.68, 3846.16]

plt.figure(figsize=(10, 6))

# Create bar chart
bars = plt.bar(riders, throughput, color=['#4fc3f7', '#2196f3', '#1976d2', '#0d47a1'])

# Add labels on top of the bars
for bar in bars:
    yval = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2.0, yval + 50, f'{yval:.0f}', ha='center', va='bottom', fontweight='bold')

# Styling
plt.title('Kafka End-to-End Throughput vs. Concurrent Riders', fontsize=15, fontweight='bold', pad=20)
plt.xlabel('Number of Concurrent Riders (Load)', fontsize=12)
plt.ylabel('Throughput (Messages / Second)', fontsize=12)
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.gca().set_axisbelow(True)

# Save to file
plt.tight_layout()
output_file = 'benchmark_results.png'
plt.savefig(output_file, dpi=300)

print(f"Successfully generated graph: {output_file}")
