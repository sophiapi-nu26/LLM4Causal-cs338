import networkx as nx
import matplotlib.pyplot as plt

def plot_graphml(
    input_file: str,
    output_file: str = "clean_graph.png",
    shape_map: dict = None,
    layout: str = "spring",
    k: float = None,          # spacing factor for spring layout
    node_scale: int = 800,   # default node size
    font_size: int = 9       # default font size
):
    """
    Read a GraphML file and plot it with:
      - Node shapes by 'type'
      - Directed edges with arrows
      - Reduced clutter using layout spacing, transparency, and scaling
    """
    G = nx.read_graphml(input_file)

    if shape_map is None:
        shape_map = {
            "protein": "o",
            "property": "s",
            "material": "^",
            "process": "D",
        }

    # --- Layout ---
    if layout == "spring":
        pos = nx.spring_layout(G, k=k, seed=42)  # 'k' controls node spacing
    elif layout == "kamada":
        pos = nx.kamada_kawai_layout(G)
    else:
        pos = nx.spring_layout(G, k=k, seed=42)

    plt.figure(figsize=(12, 10))

    node_types = nx.get_node_attributes(G, "type")
    for ntype in set(node_types.values()):
        nodes_of_type = [n for n, t in node_types.items() if t == ntype]
        shape = shape_map.get(ntype, "o")
        nx.draw_networkx_nodes(
            G,
            pos,
            nodelist=nodes_of_type,
            node_shape=shape,
            node_size=node_scale,
            alpha=0.85,          # slight transparency
            edgecolors="black",
            label=ntype,
        )

    # Edges with arrows, transparency, and curvature
    nx.draw_networkx_edges(
        G,
        pos,
        arrows=True,
        arrowsize=18,
        arrowstyle="->",
        width=1.0,
        alpha=0.5,               # fade edges to reduce clutter
        connectionstyle="arc3,rad=0.1",  # slight curvature
    )

    # Node labels
    nx.draw_networkx_labels(
        G,
        pos,
        font_size=font_size,
        font_weight="bold",
        bbox=dict(facecolor="white", alpha=0.7, edgecolor="none", pad=0.3)
    )

    # Edge labels (relationship)
    edge_labels = nx.get_edge_attributes(G, "relationship")
    nx.draw_networkx_edge_labels(
        G,
        pos,
        edge_labels=edge_labels,
        font_size=font_size - 1,
        font_color="darkred",
        rotate=False
    )

    plt.legend(scatterpoints=1, fontsize=font_size, loc="best", frameon=True)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()
    print(f"Graph saved to {output_file}")


# Example usage:
plot_graphml("output.graphml", output_file="graph.png",
             layout="kamada", k=None, node_scale=200, font_size=8)
