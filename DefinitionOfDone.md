# Definition of Done

Every feature in LyfSync 2.0 is considered **Done** only when all of the following criteria are met. This applies to every feature issue regardless of domain or priority.

---

## ✅ Code Quality
- [ ] Code follows the conventions defined in [Coding Standards.md](./Coding%20Standards.md)
- [ ] All files remain under **400 lines of code**
- [ ] No hardcoded secrets, API keys, or credentials in source code

## ✅ Testing
- [ ] Unit tests written for all new business logic
- [ ] Integration tests written for all new API endpoints
- [ ] All existing tests still pass (no regressions)

## ✅ Documentation
- [ ] Relevant living docs updated (Architecture.md, API Contract.md, etc.)
- [ ] New endpoints documented in [API Contract.md](./API%20Contract.md)
- [ ] Any significant design decisions recorded in [Architecture.md](./Architecture.md)

## ✅ Review
- [ ] AI code review completed (bugs, edge cases, security, performance)
- [ ] Feature tested manually on the target platform (mobile/web)
- [ ] No critical or blocker bugs open against this feature

## ✅ Merge
- [ ] Feature branch merged into `main` via PR
- [ ] CI / local test suite passes 100% before merge
- [ ] Commit messages follow conventional commit format (`feat:`, `fix:`, `docs:`, etc.)

---

> This document is the single source of truth for completion criteria.
> Individual feature issues describe **what to build** and **acceptance criteria** — not this process.
