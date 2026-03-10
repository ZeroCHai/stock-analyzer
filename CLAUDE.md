# CLAUDE.md — AI Assistant Guide for ZeroCHai/Tools

This file provides context, conventions, and workflows for AI assistants (Claude Code and others) working in this repository.

## Repository Overview

**Repository:** ZeroCHai/Tools
**Purpose:** A collection of tools and utilities.
**Current state:** Newly initialized — no source files yet.

---

## Repository Structure

```
Tools/
├── CLAUDE.md          # This file — AI assistant guide
└── (tools to be added)
```

As tools are added, this structure should be updated to reflect the layout (e.g., directories per tool, shared libraries, test directories).

---

## Development Workflow

### Branching

- Feature branches must follow the pattern: `claude/<description>-<session-id>`
- Never push directly to `main` or `master` without explicit permission.
- Always create a branch before making changes:
  ```bash
  git checkout -b claude/<feature-name>-<id>
  ```

### Committing

- Write clear, descriptive commit messages in the imperative mood.
  - Good: `Add markdown linter tool`
  - Bad: `changes` or `wip`
- Stage specific files rather than `git add -A` to avoid accidentally committing secrets or build artifacts.

### Pushing

- Always push with tracking: `git push -u origin <branch-name>`
- If push fails due to network errors, retry up to 4 times with exponential backoff (2s, 4s, 8s, 16s).
- Never force-push to shared/protected branches.

### Pull Requests

- Use `gh pr create` with a clear title (under 70 characters) and a body that includes a summary and test plan.
- Link related issues when applicable.

---

## Code Conventions

### General

- Prefer editing existing files over creating new ones.
- Avoid over-engineering — implement only what is needed for the current task.
- Do not add features, refactors, or improvements beyond what was requested.
- Delete unused code rather than leaving it commented out.

### Security

- Never commit secrets, API keys, `.env` files, or credentials.
- Validate all external input (user input, external APIs). Trust internal code and framework guarantees.
- Avoid introducing OWASP Top 10 vulnerabilities (SQL injection, XSS, command injection, etc.).

### Comments & Documentation

- Add comments only where logic is non-obvious.
- Keep this `CLAUDE.md` up to date as the repository evolves.

---

## Adding New Tools

When adding a new tool to this repository:

1. Create a dedicated directory or file for the tool.
2. Include a brief description of what the tool does at the top of the file.
3. Add usage instructions (CLI flags, environment variables, expected inputs/outputs).
4. Write tests if the tool has logic worth testing.
5. Update the **Repository Structure** section of this file.

---

## AI Assistant Notes

- **Read before editing:** Always read a file before proposing changes.
- **Minimal changes:** Make only the changes required by the task.
- **Reversibility:** Prefer reversible actions; confirm with the user before destructive operations.
- **No backwards-compat hacks:** Remove unused code entirely instead of keeping stubs.
- **No guessing URLs:** Do not generate or guess URLs unless confident they are correct and helpful.

---

## 思维与回答规范

### 核心思维

运用**第一性原理**，拒绝经验主义和路径盲从。

- 不要假设用户完全清楚自己的目标——若动机模糊，**停下来讨论**，不要盲目执行。
- 若当前路径非最优，**直接建议更短、更低成本的替代办法**，而非沿用惯例。

### 强制输出结构

所有回答必须分为以下两个部分：

**[直接执行]**
按照用户当前的要求和逻辑，直接给出任务结果。

**[深度交互]**
基于底层逻辑对原始需求进行"审慎挑战"，包括但不限于：
- 质疑动机是否偏离目标（XY 问题识别）
- 分析当前路径的弊端与隐性成本
- 给出更优雅、更直接的替代方案
