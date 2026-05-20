# Mermaid Diagram PPT Replacement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the simplified flow graphics in the technical-review PowerPoint with the original Mermaid diagrams extracted from the Chinese report Markdown.

**Architecture:** Keep the current PPT structure and template background, extract Mermaid blocks from the report Markdown, render them as image assets, then overlay those rendered diagrams onto the corresponding slides in the generated PPT. Keep the replacement logic separate from Markdown extraction so the asset pipeline is testable and reusable.

**Tech Stack:** Python, `python-pptx`, local filesystem assets, Mermaid rendering, PowerPoint export for visual QA

---

### Task 1: Add testable Mermaid extraction and slide-mapping logic

**Files:**
- Create: `src/openscenario_mcp/reporting/ppt_mermaid.py`
- Create: `tests/unit/test_ppt_mermaid.py`

- [ ] **Step 1: Write failing tests for Mermaid block extraction**
- [ ] **Step 2: Verify the tests fail**
- [ ] **Step 3: Implement minimal extraction helpers**
- [ ] **Step 4: Add tests for report-specific slide replacement mapping**
- [ ] **Step 5: Verify all new tests pass**

### Task 2: Add a PPT replacement script

**Files:**
- Create: `scripts/apply_report_mermaid_diagrams.py`

- [ ] **Step 1: Write a failing test for diagram asset naming / selection if practical**
- [ ] **Step 2: Implement the replacement script using the tested helpers**
- [ ] **Step 3: Make the script accept explicit `--md`, `--ppt`, and `--assets-dir` paths**
- [ ] **Step 4: Support overlaying rendered images onto the target slide regions**

### Task 3: Render Mermaid diagrams and update the deck

**Files:**
- Create: `进展汇报/assets/mermaid/*.png`
- Modify: `进展汇报/OpenSCENARIO智能场景生成辅助平台-技术评审汇报.pptx`
- Modify: `docs/work-order.md`

- [ ] **Step 1: Extract Mermaid blocks from the Markdown report**
- [ ] **Step 2: Render the Mermaid diagrams into PNG assets**
- [ ] **Step 3: Run the replacement script against the existing PPT**
- [ ] **Step 4: Export the updated PPT to PNG previews and visually check the replaced slides**
- [ ] **Step 5: Update the work log with the new diagram-replacement deliverable**
