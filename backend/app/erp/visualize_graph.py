# visualize_graph.py

from app.erp.ERPCoach.graph import get_erp_coach_graph

graph = get_erp_coach_graph()

# get underlying graph structure
g = graph.get_graph()

# save png
g.draw_mermaid_png(output_file_path="erp_coach_graph.png")