<!--
Sync Impact Report:
- Version change: v1.0.0 -> v1.0.1
- Modified principles: None
- Modified sections:
  - Architectural & Engineering Standards: Removed premature framework and toolchain dependencies (Python 3.12, ruff, uv, Hydra) in favor of framework-agnostic engineering rules.
- Added sections: None
- Removed sections: None
- Deferred TODOs: None
-->

# GenreGuru Constitution

## Core Principles

### I. Standalone Library-First Architecture
All features MUST be implemented as standalone, independent libraries prior to integration into higher-level application components.
- Each library MUST be self-contained, independently testable, well-documented, and focused on a single responsibility.
- Libraries MUST NOT depend directly on application state or web UI components, ensuring maximum reusability and decoupling across the GenreGuru ecosystem.

### II. Extreme Programming (XP) & Incremental Iteration
Software development MUST follow Extreme Programming (XP) practices, delivering value in small, continuous, incremental releases.
- Work MUST be executed iteratively through small design cycles, continuous integration, frequent refactoring, and pair programming / agentic pairing.
- Scope MUST be broken into minimal executable increments to maximize feedback loops and reduce integration risk.

### III. Strict Test-Driven Development (TDD)
Test-Driven Development is NON-NEGOTIABLE across all codebase components.
- The Red-Green-Refactor cycle MUST be strictly enforced: automated unit tests MUST be written and confirmed failing before any implementation code is written.
- Code MUST NOT be merged or considered complete without comprehensive automated unit and integration tests validating all behavior and edge cases.

### IV. Simplicity & Modular Adaptability
Code MUST prioritize clarity, readability, and simple design ("Keep It Simple", YAGNI) while maintaining sufficient modularity to adapt to changing requirements.
- Solutions MUST address immediate, explicitly specified requirements without speculative over-engineering.
- Abstractions MUST be introduced cleanly at module boundaries so future requirement changes can be incorporated with minimal blast radius.

### V. SOLID Object-Oriented Design
All object-oriented code MUST adhere strictly to the SOLID principles:
- **Single Responsibility Principle (SRP)**: Every class/module MUST have one, and only one, reason to change.
- **Open/Closed Principle (OCP)**: Entities MUST be open for extension, but closed for modification.
- **Liskov Substitution Principle (LSP)**: Derived classes MUST be substitutable for their base types without altering program correctness.
- **Interface Segregation Principle (ISP)**: Clients MUST NOT be forced to depend upon interfaces they do not use.
- **Dependency Inversion Principle (DIP)**: High-level modules MUST depend on abstractions, not concrete implementations.

## Architectural & Engineering Standards
- **Framework & Technology Agnosticism**: Governance MUST NOT prescribe specific frameworks, libraries, or toolchains. Tooling and stack decisions MUST be determined dynamically during feature specification and planning.
- **Explicit Interfaces & Contracts**: Modules MUST communicate through clearly specified interfaces or abstract contracts rather than relying on implicit state or direct structural coupling.
- **Root-Cause Defect Resolution**: Runtime failures and failing tests MUST be diagnosed to root cause before applying code fixes. Masking symptoms, suppressing errors, or introducing silent fallback defaults without handling is strictly prohibited.

## Development & Quality Workflow
- **Red-Green-Refactor Cycle**:
  1. Write failing unit/integration tests defining expected behavior.
  2. Implement minimal code to pass tests.
  3. Refactor for clarity, simplicity, and SOLID alignment while ensuring tests remain green.
- **Continuous Verification**: All changes MUST pass linting, type checks, and full test suites prior to finalizing tasks.

## Governance
- This Constitution supersedes all informal development practices. All features, pull requests, and agentic workflows MUST strictly comply with these principles.
- Amendments to this constitution require explicit justification, semantic versioning increments, and updates to `.specify/memory/constitution.md`.
- **Versioning Policy**:
  - **MAJOR (X.0.0)**: Incompatible principle removals or foundational governance shifts.
  - **MINOR (1.X.0)**: Addition of new core principles or major architectural sections.
  - **PATCH (1.0.X)**: Wording clarifications, formatting adjustments, and non-semantic refinements.

**Version**: 1.0.1 | **Ratified**: 2026-08-03 | **Last Amended**: 2026-08-03
