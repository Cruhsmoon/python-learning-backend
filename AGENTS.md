# AGENTS.md

## Project overview
This is a TypeScript project.
The goal is to keep the codebase clean, testable, and production-ready.

## Setup commands
- Install dependencies: `pnpm install`
- Start dev server: `pnpm dev`
- Run tests: `pnpm test`
- Type check: `pnpm tsc --noEmit`

## Code standards
- TypeScript strict mode is required
- Use single quotes
- No semicolons
- Prefer functional patterns over classes
- Avoid `any` unless absolutely necessary
- All new logic must be covered by tests

## Testing guidelines
- Write unit tests for all business logic
- Cover edge cases and negative scenarios
- Prefer deterministic tests
- Avoid flaky tests

## Architecture guidelines
- Keep functions small and pure where possible
- Separate business logic from IO
- Avoid tight coupling between modules
- Follow dependency inversion when applicable

## Pull request expectations
- No console logs in production code
- All tests must pass
- No unused imports
- No commented-out code
## Agent behavior
When modifying code:
- Do not change unrelated files
- Explain reasoning before major refactoring
- Suggest improvements but do not over-engineer
