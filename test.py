# We'll build a GraphML file representing causal and correlational relationships
# extracted from the provided paper. Nodes will be typed as one of:
# Material, Structure, Property, Process. Edges will be labeled with one of:
# 'increase', 'decrease', 'cause', 'correlate_with'.
#
# We'll use networkx to create and save the graph.

import networkx as nx

G = nx.DiGraph()

def add_node(name, category):
    G.add_node(name, category=category)

def add_edge(src, dst, relation, note=""):
    # relation must be one of {'increase','decrease','cause','correlate_with'}
    G.add_edge(src, dst, relation=relation, note=note)

# Materials
add_node("MaSp1", "Material")
add_node("MaSp2", "Material")
add_node("MaSp3", "Material")
add_node("Multicomponent MaSp1–3", "Material")
add_node("SpiCE proteins", "Material")

# Structures (sequence/meso-structure features)
add_node("Polyalanine length/frequency", "Structure")
add_node("β-sheet region length", "Structure")
add_node("Amorphous region length", "Structure")
add_node("Amorphous:β-sheet length ratio", "Structure")
add_node("Motif: MaSp1-AGQG", "Structure")
add_node("Motif: MaSp2-AAAAAAAA", "Structure")
add_node("Motif: MaSp1-YGQGG", "Structure")
add_node("Motif: MaSp1-GYGQGG", "Structure")
add_node("Motif: MaSp1-GGS after poly-Ala", "Structure")
add_node("Motif: MaSp1-SY / SV", "Structure")
add_node("Pro in MaSp2 amorphous region", "Structure")
add_node("Ser in MaSp1 amorphous region", "Structure")
add_node("Birefringence (molecular orientation)", "Structure")
add_node("Crystallinity (WAXS)", "Structure")
add_node("Diameter", "Structure")

# Processes
add_node("Wetting / Hydration", "Process")

# Properties
add_node("Toughness", "Property")
add_node("Tensile strength", "Property")
add_node("Strain at break (extensibility)", "Property")
add_node("Young's modulus", "Property")
add_node("Supercontraction", "Property")
add_node("Thermal degradation temperature", "Property")
add_node("Water content", "Property")

# Relationships from the paper

# High-level material effects
add_edge("MaSp3", "Toughness", "increase", note="Presence associated with +0.041 GJ/m3 toughness; strong determinant")
add_edge("MaSp2", "Supercontraction", "increase", note="Multiple MaSp2 groups associated with +11–15.8% supercontraction")
add_edge("MaSp2", "Strain at break (extensibility)", "increase", note="MaSp2 specialized for elasticity; determinant for strain at break")
add_edge("MaSp1", "Tensile strength", "increase", note="MaSp1 specialized for strength")
add_edge("Multicomponent MaSp1–3", "Toughness", "increase", note="Combination of paralogs yields high toughness")
add_edge("SpiCE proteins", "Tensile strength", "cause", note="SpiCE doubled tensile strength of artificial film in vitro")

# Sequence/structural features and properties
add_edge("Polyalanine length/frequency", "Supercontraction", "decrease", note="Poly-Ala strongly negatively correlated with supercontraction")
add_edge("β-sheet region length", "Supercontraction", "decrease", note="Longer β-sheet (poly-A/S/V) negatively correlated")
add_edge("Amorphous:β-sheet length ratio", "Supercontraction", "cause", note="Key contributing factor; higher ratio promotes supercontraction")
add_edge("Motif: MaSp1-AGQG", "Supercontraction", "correlate_with", note="Positive correlation")
add_edge("Motif: MaSp2-AAAAAAAA", "Supercontraction", "correlate_with", note="Negative correlation")
add_edge("Motif: MaSp1-YGQGG", "Toughness", "correlate_with", note="Positive correlation; also with strength/strain")
add_edge("Motif: MaSp1-GYGQGG", "Toughness", "correlate_with", note="Positive correlation; also with strength/strain")
add_edge("Motif: MaSp1-GGS after poly-Ala", "Toughness", "correlate_with", note="Positive correlation")
add_edge("Motif: MaSp1-SY / SV", "Toughness", "correlate_with", note="Negative correlation")
add_edge("Pro in MaSp2 amorphous region", "Tensile strength", "decrease", note="Negative effect on strength")
add_edge("Pro in MaSp2 amorphous region", "Toughness", "decrease", note="Negative correlation with toughness")
add_edge("Ser in MaSp1 amorphous region", "Tensile strength", "increase", note="Positive influence on strength")

# Mesostructure-property correlations
add_edge("Birefringence (molecular orientation)", "Tensile strength", "correlate_with", note="Good predictor of strength (positive)")
add_edge("Crystallinity (WAXS)", "Strain at break (extensibility)", "correlate_with", note="Predictor for strain at break")
add_edge("Diameter", "Strain at break (extensibility)", "correlate_with", note="Correlation reported")
add_edge("Diameter", "Supercontraction", "correlate_with", note="Correlation reported (caveat: pseudo-correlation)")

# Property-property correlations
add_edge("Toughness", "Tensile strength", "correlate_with", note="Toughness correlated with strength")
add_edge("Toughness", "Strain at break (extensibility)", "correlate_with", note="Toughness correlated with strain at break")
add_edge("Toughness", "Young's modulus", "correlate_with", note="Toughness correlated with modulus")

# Process relations
add_edge("Wetting / Hydration", "Supercontraction", "cause", note="Wetting triggers supercontraction (up to ~60%)")

# Extra properties observed to improve with Araneidae & related groups
add_edge("MaSp3", "Strain at break (extensibility)", "increase", note="Araneidae superiority included strain at break, crystallinity, diameter, Td, supercontraction")
add_edge("MaSp3", "Crystallinity (WAXS)", "increase", note="Family-level superiority; included crystallinity")
add_edge("MaSp3", "Thermal degradation temperature", "increase", note="Family-level superiority; included Td")

# Save to GraphML
out_path = "./silk_causal_graph.graphml"
nx.write_graphml(G, out_path)
out_path
