# OpenSCENARIO Technical Review PPT Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a detailed technical-review PowerPoint in the current repo using the existing template background and the finalized Chinese report as the source.

**Architecture:** Copy the existing template `.pptx`, preserve its background/master styling on every slide, then programmatically generate a high-density deck with structured text, custom diagrams, and module examples. Use local automation to inspect the template and export preview images for slide-level QA.

**Tech Stack:** `python-pptx`, `Pillow`, Windows PowerPoint COM automation, local Markdown source report

---

### Task 1: Inspect template and source assets

**Files:**
- Read: `进展汇报/项目研究计划(1).pptx`
- Read: `进展汇报/OpenSCENARIO智能场景生成辅助平台-阶段性技术汇报.md`

- [ ] **Step 1: Confirm template layouts and blank background slides**

Run:

```powershell
@'
from pathlib import Path
from pptx import Presentation
p = next(Path('.').glob('**/*.pptx'))
prs = Presentation(str(p))
print({'slides': len(prs.slides), 'layouts': len(prs.slide_layouts)})
'@ | py -3.14 -
```

- [ ] **Step 2: Export template preview slides for visual confirmation**

Run:

```powershell
$pptPath = (Get-ChildItem '进展汇报' -Filter *.pptx | Select-Object -First 1).FullName
$outDir = Join-Path $PWD '.codex-tmp\ppt-template-preview'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$ppt = New-Object -ComObject PowerPoint.Application
$ppt.Visible = -1
$pres = $ppt.Presentations.Open($pptPath, $false, $true, $false)
$pres.Export($outDir, 'PNG')
$pres.Close()
$ppt.Quit()
```

### Task 2: Generate the technical-review PPT

**Files:**
- Create: `scripts/build_progress_report_ppt.py`
- Create: `进展汇报/OpenSCENARIO智能场景生成辅助平台-技术评审汇报.pptx`

- [ ] **Step 1: Implement PPT builder script**
- [ ] **Step 2: Copy template and append 22-24 technical-review slides**
- [ ] **Step 3: Add structured diagrams, examples, and module breakdown pages**
- [ ] **Step 4: Save generated deck to the report folder**

### Task 3: Visual QA and output verification

**Files:**
- Modify: `docs/work-order.md`

- [ ] **Step 1: Export generated slides to PNG for QA**
- [ ] **Step 2: Spot-check title page, diagram-heavy pages, and example pages**
- [ ] **Step 3: Update work log with the PPT deliverable**
