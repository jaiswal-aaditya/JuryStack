# Frontend feature boundaries

Product UI is added by domain under `auth`, `events`, `teams`, `projects`,
`judging`, and `results`. Each feature will own its pages, API contracts,
queries, forms, and focused components; genuinely reusable primitives belong in
`shared`.
