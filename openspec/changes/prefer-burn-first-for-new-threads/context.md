# Context

Codex identifies both a process and its logical threads. A newly seen thread
inherits the process's account preference to retain locality. The previous
implementation tested that one account alone, so ordinary burn_first priority
never saw an available primary account before the new mapping was persisted.

This change affects only that initial soft preference. It does not migrate an
existing thread or override required response, conversation, file or turn-state
ownership. The existing selector decides eligibility and health ordering; a
burn_first account with exhausted quota, cooldown or a full local cap cannot
force the new thread onto it. Fixed-order routing strategies keep their rules.

Example: a process prefers normal account B after primary account A exhausted
its quota. When A recovers, a new thread chooses A (burn_first), while existing
thread mappings to B and the process preference itself stay intact.
