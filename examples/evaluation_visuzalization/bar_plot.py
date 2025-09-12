import matplotlib.pyplot as plt
import numpy as np

plt.rcParams['font.family']='serif'
plt.rcParams['font.size']=16

xlabel = ['GPT', 'CAMEL']
correctness = [0.615,0.923]
strain_at_break = [0.286,0.571]
toughness = [0.25,0.833]
modulus = [0.333,0.556]

# Colors (light pastels)
gpt_color = '#c6dbef'   # light blue
ours_color = '#c7e9c0'  # light green

def style_ax(ax):
    ax.grid(axis='y', linestyle='-', linewidth=1, alpha=0.25)
    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_visible(False)  # no bounding box
    ax.tick_params(axis='both', length=0)
    ax.set_ylim(0, 1)

def add_value_labels(ax, bars, dy=0.02):
    for b in bars:
        h = b.get_height()
        ax.text(b.get_x() + b.get_width()/2, h + dy, f'{h:.3f}',
                ha='center', va='bottom', fontsize=12)

# --- Figure 1: Correctness ---
fig, ax = plt.subplots(figsize=(8, 6))
bars = ax.bar(xlabel, correctness, width=0.6,
              color=[gpt_color, ours_color],
              edgecolor="black",  # outline
             linewidth=1.4)
ax.set_ylabel("Score (0–1)")
ax.set_title("Correctness")
style_ax(ax)
add_value_labels(ax, bars)
plt.tight_layout()
plt.savefig('correctness.png', dpi=300, bbox_inches='tight')
plt.close(fig)

# --- Figure 2: Completeness (grouped bars) ---
metrics = ['Strain at break', 'Toughness', "Young's modulus"]
gpt_vals = [strain_at_break[0], toughness[0], modulus[0]]
ours_vals = [strain_at_break[1], toughness[1], modulus[1]]

x = np.arange(len(metrics))
w = 0.36

fig, ax = plt.subplots(figsize=(9, 6))
bars1 = ax.bar(x - w/2, gpt_vals, width=w, label='GPT',
               color=gpt_color, edgecolor='black')
bars2 = ax.bar(x + w/2, ours_vals, width=w, label='CAMEL',
               color=ours_color, edgecolor='black')

ax.set_xticks(x, metrics, rotation=10)
ax.set_ylabel("Score (0–1)")
ax.set_title("Completeness")
style_ax(ax)
add_value_labels(ax, bars1)
add_value_labels(ax, bars2)
leg = ax.legend(frameon=False)

plt.tight_layout()
plt.savefig('completeness.png', dpi=300, bbox_inches='tight')
plt.close(fig)

