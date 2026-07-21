---
name: job-search
description: Guided search and realistic ranking of active jobs from the Job Scout offer database. Use for any Polish or English request to find, compare, filter, or rank jobs, including terse prompts such as "znajdź mi pracę", "coś spokojniejszego", "więcej kasy", "remote DevOps", or "what should I apply to?" Also use to create, show, update, or improve the user's candidate profile and job preferences, including an optional review of missing, unclear, or inconsistent CV evidence.
allowed-tools:
  - mcp__jobscout__get_catalog_facets
  - mcp__jobscout__search_offers
  - mcp__jobscout__search_many
  - mcp__jobscout__get_offer
  - mcp__jobscout__batch_get_offers
  - mcp__plugin_jobscout_jobscout__get_catalog_facets
  - mcp__plugin_jobscout_jobscout__search_offers
  - mcp__plugin_jobscout_jobscout__search_many
  - mcp__plugin_jobscout_jobscout__get_offer
  - mcp__plugin_jobscout_jobscout__batch_get_offers
---

# Job Scout search

Use the Job Scout MCP as the only source of offers. It is a read-only catalog; never substitute
web search or invented offers when its tools are available.

## Connection gate

Before starting an offer search, verify that `get_catalog_facets`, `search_many`, and
`batch_get_offers` exist under either the user-scoped `mcp__jobscout__*` names or plugin-scoped
names. `search_offers` and `get_offer` are compatibility fallbacks for older servers. If they are
absent, stop immediately. Do not inspect plugin JSON, Keychain, tool registries, or broaden to web
search.

In Claude Code, tell the user to configure the read-only MCP in a terminal and start a new session:

```sh
read -s "JOBSCOUT_MCP_KEY?Job Scout MCP key: "
echo
claude mcp add --transport http --scope user jobscout \
  https://praca-mcp.micek.top/mcp \
  --header "Authorization: Bearer $JOBSCOUT_MCP_KEY"
unset JOBSCOUT_MCP_KEY
```

In Cowork or Claude Chat, tell the user to open **Customize -> Connectors**, choose **+ -> Add
custom connector**, and enter the private capability URL supplied by the Job Scout operator. Then
start a new task and enable `Job Scout` from **+ -> Connectors**. Never ask the user to paste the
key or capability URL into chat. Local MCP configuration from Claude Code is not available in
Cowork, and `/reload-plugins` cannot make it available there.

In Codex, tell the user to paste `https://github.com/olekgoli/jobscout-codex` into a local task and ask
Codex to install it. The installing agent must inspect and run `install_codex.py`; its hidden
local prompt collects the MCP key without putting it in chat. Start a new task after restarting
Codex.

## Candidate profile

Keep each user's private profile at:

```text
${JOBSCOUT_PROFILE_PATH:-$HOME/.config/jobscout/profile.md}
```

Interpret that expression in the shell: `JOBSCOUT_PROFILE_PATH` overrides the default. Never put
the MCP key, CV contents, contact details, or other secrets in the profile. Create parent
directories when saving. Do not store the profile in the plugin directory or production service.

At the start of every Claude Code job request, resolve the path with
`printf '%s\n' "${JOBSCOUT_PROFILE_PATH:-$HOME/.config/jobscout/profile.md}"`, then check and read
that exact path. Do not assume the default when the override is set. Treat a request's new
constraints as one-search overrides. Change the saved profile only when the user explicitly asks
or completes onboarding.

In Cowork, use `profile.md` in the task's connected working folder instead. The sandbox home
directory is not the user's persistent local profile store. If no working-folder profile is
available, ask the user to attach an existing `profile.md` or run onboarding and save the generated
profile in that folder. Do not claim persistence until the file exists there.

### First use

If no profile exists, do not search yet. Say that setup happens once, accepts "nie wiem", and ask
the following four short rounds one at a time. When a CV is provided, extract only explicit facts
and skip questions it already answers.

1. **Current evidence:** recent roles, internships, and relevant projects with dates; daily
   responsibilities; strongest achievements; technologies usable independently from day one;
   technologies used with support. Label commercial and non-commercial evidence separately.
2. **Practical constraints:** target role families and seniority; remote/hybrid and work location;
   contract types; minimum and preferred monthly PLN; languages; availability.
3. **Direction:** responsibilities wanted more/less often; technologies being learned; technologies
   the user wants to learn at work; known gaps that must not be required on day one; sectors liked
   or avoided.
4. **WLB:** tolerance for on-call, incidents, 24/7 systems, overtime/weekends, production ownership,
   travel and foreign time zones; preferred pace; whether pay, learning, stability, or low stress
   should dominate ranking.

When a CV was provided, offer an optional evidence review before saving the profile:

1. Summarize at most five profile-relevant details that are missing, unclear, or inconsistent.
   Prioritize dates and duration, actual role scope, independent versus supported work, technology
   context and recency, and achievement scale or outcome. Ground every finding in the CV or the
   user's answers; missing information alone is not a contradiction.
2. Propose one focused clarification question per finding and ask whether the user wants to answer
   them. This pass is optional: if the user declines, skips a question, or stops, continue without
   pressure and keep unresolved items under `Unknowns`.
3. If accepted, ask the questions one at a time and update the profile only from explicit answers.

After round four, save a concise Markdown profile with this structure:

```markdown
# Job Scout candidate profile
Updated: YYYY-MM-DD

## Proven day-one skills
## Working knowledge
## Learning now
## Must not be required on day one
## Experience evidence
## Target work
## Search defaults
## Growth goals
## WLB guardrails
## Ranking priorities
## Unknowns
```

Never merge the four technology buckets. "Wants to learn" is not experience, and a skill required
from day one is not a learning opportunity. Record unknown answers under `Unknowns`; do not infer
experience from job titles. Save to the surface-specific location above, tell the user where the
profile was saved, and then ask for the first search request.

### Existing profile

Do not repeat onboarding. A terse prompt must be enough. Ask a follow-up only when a missing answer
would materially change hard filtering; otherwise use the saved defaults and state the assumption.
When the user asks to improve the profile or supplies a new CV, offer the same optional evidence
review before saving any explicit profile update.

## Non-negotiable ranking rules

Apply these literally, even when they leave fewer results than requested:

1. Anything listed under `Must not be required on day one` is an absolute veto when the offer makes
   it mandatory. Do not relabel it "learnable", "basic", or "stretch". Put that offer only under
   near-misses.
2. A skill from `Learning now`, `Working knowledge`, or `Growth goals` is never a proven day-one
   skill. Do not print it under "why day-one fits". It is a learning opportunity only when the
   offer does not require independent competence from day one.
3. An explicit WLB conflict is an absolute veto when WLB is the top priority. A sector, SRE title,
   observability, monitoring, alerts, "global" team, benefits, or company size are not evidence of
   on-call or poor WLB, however plausible the inference. They justify a recruiter question, never
   a veto or probability claim. Absence of on-call wording is not evidence of good WLB either; use
   `unknown / do potwierdzenia`.
4. Never pad a ranking. Zero or one eligible offer is a valid result.

Immediately before answering, make an internal table for each finalist: mandatory requirements
proven, absolute-veto gap, explicit WLB conflict, WLB evidence. Remove every row with a veto or
conflict. Then re-check that each claimed proven skill appears literally in `Proven day-one skills`.
Never infer Linux, Git, YAML, scripting, containers, or any other technology from a role title or
from an Azure/DevOps background.

## Search workflow

1. Call `get_catalog_facets` when exact filter values are not already known.
2. Turn remote mode, contracts, working time, dates, location, and salary floor into shared
   `search_many` filters. `salary_min` means an option can reach that monthly amount; verify the
   relevant contract and actual range in offer details.
3. Build one diversified `search_many` request from target role families, proven day-one skills,
   desired responsibilities, and learning goals. Give every search a stable ID. Use `expression`
   with `must`, `should`, `must_not`, `any_of`, `all_of`, `exact_phrase`, and documented fields
   when alternatives or exclusions improve recall; do not invent `boost` or other operators.
4. Include one adjacent-role pass based on responsibilities, not just titles. Useful families can
   include cloud automation, release/build engineering, integration engineering, infrastructure,
   developer enablement, platform operations, and internal tooling when supported by the profile.
5. Follow `next_cursor` on the same search set until `coverage.complete` is true. Report
   `raw_match_count`, `unique_offer_count`, overlap, and per-search contribution; never claim full
   coverage from a partial snapshot.
6. The union is already de-duplicated. Use `why_matched`, source requirement evidence,
   `compensation_summary`, and quality flags only to discard obvious mismatches. Fetch every
   plausible candidate, up to 30, in one `batch_get_offers(detail_level="screening")` call; use
   `full` only where unresolved source details matter.
7. Rank from full details. Separate explicit evidence from inference and missing information.

## Realistic admission gate

Reject offers where the user has a low realistic chance, especially when several unknown skills,
expert ownership, or many years of direct production experience are mandatory from day one.
Distinguish:

- a quick learnable gap such as a neighboring CI/CD tool or syntax;
- a stretch gap that needs supervised production exposure;
- a blocking gap such as expert Kubernetes operations, a required programming language, deep
  security specialization, or lead ownership absent from the profile.

Nice-to-have gaps do not block. Prefer roles matching the target seniority and evidence in the
profile. For junior candidates, count internships and academic or personal projects when an offer
accepts non-commercial evidence, keep them labeled as such, and prefer roles with supervised
growth. For senior candidates, require explicit evidence of any mandatory scope, ownership,
mentoring, and impact. Keep at most two honest stretch offers and label them clearly. Never turn
"familiarity" or a project into commercial experience. If the profile does not state years or
seniority evidence required by an offer, admission chance cannot be `high`.

## WLB gate

Apply saved WLB preferences before maximizing technology match. Penalize explicit on-call,
standby, incident response, 24/7 systems, evening/weekend deploys, sole production ownership,
cluster upgrade ownership, SRE reliability pressure, incompatible time zones, travel, and very
broad one-person responsibility. Unknown WLB is not positive evidence: label it "do potwierdzenia".
Company sector alone is only a weak signal.

For requests such as "lekko", "spokojnie", or "WLB najważniejsze", exclude explicit WLB conflicts
and rank low operational pressure first. For "odrobinę trudniejsze", allow one supervised stretch
area but not expert-level ownership or multiple blocking gaps.

## Result format

Return the requested number of eligible offers, or up to 10 by default, strongest first. For each
include:

- role, company, compensation and contract, remote/location status, direct source link;
- realistic admission chance: high / medium / stretch, with concrete evidence;
- WLB outlook and confidence: good / neutral / risky / unknown;
- why it fits day-one skills;
- learning opportunity and gaps;
- questions to verify with the recruiter.

Finish with up to three near-misses and the exact rejection reason when that helps the user avoid
wasted applications. State catalog coverage, filters, result count, and any unverified remote,
salary, Poland eligibility, or WLB assumptions. Do not claim filters the MCP cannot express and do
not claim certainty about hiring chances or company culture. Any required or occasional office
visit means `remote with visits`, never `100% remote`.
