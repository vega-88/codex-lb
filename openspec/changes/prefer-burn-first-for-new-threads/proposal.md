# Prefer burn-first accounts for newly seeded threads

A new Codex thread can inherit a normal account from its process preference
before manual routing policy is considered, even when an eligible burn_first
account has recovered its quota. This makes a fresh thread consume reserve
capacity despite the operator's manual priority.

For a previously unmapped thread, consider eligible burn_first accounts together
with the inherited preference using existing account selection. Keep the process
mapping unchanged and persist only the selected new thread mapping. Existing
thread mappings and required response/file/turn-state owners remain unchanged.
Health, quota, scope, local caps and fixed-order strategy semantics still apply.
No settings, schema, migrations or request payload changes are required.
