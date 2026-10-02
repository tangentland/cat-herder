---
gmd: "0.1"
id: cat-herder/architecture-readme
title: "{PROJECT_NAME} — Architecture Overview"
tags: [architecture, overview]
---

# {PROJECT_NAME} — Architecture Overview {#root}

One-paragraph statement of what the system is and the problem it solves. Replace this
with your project's actual overview during setup.

## System Shape {#system-shape}

Describe the major subsystems and how they relate. Keep this high level — details live in
the per-topic docs linked from [[architecture-index#root]].

## Design Tenets {#design-tenets}

List the load-bearing principles every design proposal must reason FROM (not around).
Each tenet should be falsifiable and citable by ADRs.

## Navigation {#navigation}

- Index of all architecture docs: [[architecture-index#root]]
- Decision records: `adr/`
- Concept docs: `concepts/`
- Design-space research: `explorations/`
- Tracked gaps: [[architecture-todo#root]]

rel: catalogs -> [[architecture-index]]
rel: depends-on -> [[architecture-todo]]
