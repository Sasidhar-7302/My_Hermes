# Paper MCP Loop

Use this fixed loop for reliable Paper execution:

1. Read file context with `get_basic_info` and `get_selection`.
2. If editing existing nodes, inspect hierarchy with `get_tree_summary`, `get_children`, or `get_node_info`.
3. Read typography constraints with `get_font_family_info`.
4. Plan artboards/components before writing.
5. Make 1-3 grouped edits only.
6. Capture a screenshot with `get_screenshot`.
7. Critique spacing, hierarchy, contrast, clipping, and density.
8. Repair if needed.
9. Continue until the artboard set is coherent.
10. Finish with `finish_working_on_nodes`.

Write policy:

- Prefer `set_text_content` and `update_styles` for targeted changes.
- Use `write_html` for new grouped structure, repeated shells, and fast screen bootstrapping.
- Keep edits reversible and compositional.
