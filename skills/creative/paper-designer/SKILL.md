---
name: paper-designer
description: "Inspect, design, audit, and generate professional UI/UX artboards and components in Paper Desktop via native HTTP MCP."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, macos]
metadata:
  hermes:
    tags: [Paper, Design, UI, UX, Figma-Alternative, Wireframing, MCP]
    category: creative
    related_skills: [claude-design, design-md, excalidraw]
---

# Paper Designer Skill

Use this skill when Hermes must inspect, create, audit, or build user interfaces, dashboards, artboards, and components in Paper Desktop through its native MCP server (`http://127.0.0.1:29979/mcp`).

## When to Use

Trigger whenever the user asks to:
- Design in Paper Desktop ("design a dashboard in Paper", "create an artboard in Paper")
- Generate web/mobile UI components directly on the Paper canvas
- Inspect or audit existing Paper designs (`get_basic_info`, `get_tree_summary`, `get_selection`)
- Add or modify copy/typography in Paper (`set_text_content`, `get_font_family_info`)
- Write styled HTML into Paper artboards (`write_html`)

## Architecture & Integration

Paper Desktop exposes an HTTP JSON-RPC 2.0 MCP server with Server-Sent Events (SSE) streaming at:
`http://127.0.0.1:29979/mcp`

Hermes connects natively through `local_model_lab.paper_client.get_paper_client()`.

### Core Workflow:

1. **Check Status**: Verify Paper is listening and has an open document via `client.status()`.
2. **Read Canvas Context**: Call `get_basic_info()` and `get_selection()`.
3. **Inspect Hierarchy**: Call `get_tree_summary()` or `get_children(node_id)` before mutating nodes.
4. **Plan Artboard**: Decide layout, resolution (e.g. 1440x900 for desktop, 393x852 for mobile), and color palette.
5. **Create Artboard**: Call `create_artboard(name="Dashboard", width=1440, height=900)`.
6. **Render HTML**: Write clean, semantic HTML into the artboard with `write_html(html=..., target_node_id=artboard_id)`.
7. **Refine Typography**: Use `set_text_content()` and `update_styles()` for precise tweaks.
8. **Finalize**: Always finish with `finish_working()`.

## Enterprise Design Patterns

When designing SaaS, admin, dashboard, or consumer product screens:

- **Dashboard**: Nav rail/bar, KPI cards strip (with delta badges), trend charts area, data table with search/filter, and activity feed.
- **CRUD Workspace**: Sidebar filters, multi-column data table, side preview drawer, action toolbar.
- **Settings**: Categorized navigation, grouped cards with clear section headers, form inputs, toggle switches, and audit logs.
- **Design Tokens**:
  - Backgrounds: Neutral light (`#f8fafc` or `#ffffff`), subtle borders (`#e2e8f0`).
  - Typography: Strong primary hierarchy (`Inter`, `system-ui`, bold 24px/18px titles, 14px regular body, 12px muted meta).
  - Accents: Restrained brand color (`#2563eb` or `#059669`) reserved for primary CTAs and active states.
  - Spacing: 8px grid system (padding 16px, 24px, 32px).
