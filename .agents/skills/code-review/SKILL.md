---
name: code-review
description: Conduct rigorous code reviews focusing on bug prevention, edge cases, maintainability, and domain-specific logic integrity.
---

# Code Review Best Practices

## 1. Core Principles
- **No Speculative Assumptions**: Ground every observation in the actual code lines and verified execution paths.
- **Side Effect Prevention**: Always inspect callers and dependencies before approving or writing changes.
- **Fail-Fast & Data Integrity**: Check for None/null values, boundary conditions, and type safety at ingestion points.

## 2. Review Checklist
### Backend (Python / FastAPI)
- **Error Handling**: Are external API calls (e.g. scrapers, DB queries) wrapped in proper `try-except` blocks with meaningful logging?
- **Resource Management**: Are database sessions, file handles, or network sockets properly closed or used with context managers?
- **Data Mutation**: Are original data structures (like settlement CSVs or snapshots) protected from accidental in-place overwrites?

### Frontend (React / TypeScript)
- **Single Source of Truth**: Is business computation offloaded to the backend instead of recalculating in UI components?
- **Memoization & Rerender**: Are heavy array filters or formatting functions properly memoized (`useMemo`) where appropriate?
- **Strict Typing**: Avoid `any`. Ensure payload types match backend Pydantic schemas.

## 3. Feedback Format
1. **Critical Issues**: Bugs, memory leaks, data corruption risks.
2. **Logic & Architecture**: Consistency with domain requirements and single truth principles.
3. **Suggestions**: Performance micro-optimizations, naming, and readability improvements.
