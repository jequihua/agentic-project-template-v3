# Question Policy

When the agent cannot safely decide because evidence or ownership lives outside
the repo, it should write a question artifact instead of inventing an answer.

Questions live under `questions/open/`.

Answers live under `questions/answered/` and should cite who answered, when, and
what later artifacts should treat as authoritative.

Question statuses:
- open
- answered
- superseded
- withdrawn

Use questions for:
- external platform practice;
- unresolved product authority;
- unclear data ownership;
- credential or cost decisions;
- architecture choices outside the active scope.

