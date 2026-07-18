# 1. Record Architecture Decisions

Date: 2026-07-18

## Status
Accepted

## Context
We need a structured way to record architectural decisions so that future developers (and interviewers) understand the technical constraints, trade-offs, and design patterns established in this project.

## Decision
We will use Architectural Decision Records (ADRs) to document all major design choices. These records will be stored in `docs/adr/` in markdown format and numbered sequentially.

## Consequences
- Every significant change in architecture (e.g., swapping a framework, database driver, or testing strategy) must be documented in a new ADR.
- Code reviews will reference these documents to ensure implementations match agreed architectural directions.
