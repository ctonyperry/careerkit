"""careerkit — deterministic core of the memory-excavation resume system.

LLM steps (JD parsing, question phrasing refinement, bullet writing) run in
Claude Code chat and exchange files with this package. This code owns the
deterministic parts: data loading, coverage math, ranking, and blocking
validation. The LLM never has blocking authority; the human confirms.
"""
