#!/usr/bin/env python3
"""Build the local interactive textbook from exam-preparation-guide.md."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GUIDE = (ROOT / "exam-preparation-guide.md").read_text(encoding="utf-8")
OUT = ROOT / "study-book.html"


def md_inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank" rel="noreferrer">\1</a>', text)
    return text


def md_to_html(src: str) -> str:
    lines = src.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            fence = [""]
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                fence.append(lines[i])
                i += 1
            out.append("<pre><code>" + html.escape("\n".join(fence).lstrip("\n")) + "</code></pre>")
            i += 1
            continue
        if re.match(r"^\|", line) and i + 1 < len(lines) and re.match(r"^\|\s*[-:]+", lines[i + 1]):
            rows = []
            while i < len(lines) and re.match(r"^\|", lines[i]):
                rows.append(lines[i])
                i += 1
            body = []
            for ridx, row in enumerate(rows):
                if ridx == 1:
                    continue
                cells = [md_inline(c.strip()) for c in row.strip().strip("|").split("|")]
                tag = "th" if ridx == 0 else "td"
                body.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>")
            out.append("<table>" + "".join(body) + "</table>")
            continue
        m = re.match(r"^(#{2,4})\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            out.append(f"<h{level}>{md_inline(m.group(2))}</h{level}>")
            i += 1
            continue
        if re.match(r"^---+$", line):
            i += 1
            continue
        if re.match(r"^[-*]\s+", line) or re.match(r"^\d+\.\s+", line):
            ordered = bool(re.match(r"^\d+\.\s+", line))
            items = []
            while i < len(lines) and (re.match(r"^[-*]\s+", lines[i]) or re.match(r"^\d+\.\s+", lines[i])):
                items.append(re.sub(r"^([-*]|\d+\.)\s+", "", lines[i]))
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{md_inline(x)}</li>" for x in items) + f"</{tag}>")
            continue
        if not line.strip():
            i += 1
            continue
        para = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{2,4}\s+|```|\||[-*]\s+|\d+\.\s+|---+)", lines[i]):
            para.append(lines[i])
            i += 1
        out.append("<p>" + md_inline(" ".join(para)) + "</p>")
    return "\n".join(out)


def split_h2(src: str) -> list[tuple[str, str]]:
    parts = re.split(r"(?m)^## ", src)
    chapters = []
    for part in parts[1:]:
        title, _, body = part.partition("\n")
        chapters.append((title.strip(), body.strip()))
    return chapters


CHAPTERS = split_h2(GUIDE)
CHAPTER_HTML = {title: md_to_html("## " + title + "\n\n" + body) for title, body in CHAPTERS}


def chapter(*titles: str) -> str:
    blocks = []
    for title in titles:
        if title not in CHAPTER_HTML:
            raise KeyError(title)
        blocks.append(CHAPTER_HTML[title])
    return "\n".join(blocks)


def box(kind: str, kicker: str, body: str) -> str:
    return f'<div class="card {kind}"><div class="kicker">{html.escape(kicker)}</div>{body}</div>'


def skills(items: list[str]) -> str:
    lis = "".join(f"<li>{md_inline(x)}</li>" for x in items)
    return box("ok", "You must be able to", f"<ul>{lis}</ul>")


CHECKS = {
    "1.1": [
        ("The assistant text says the refund is done, but stop_reason is tool_use. What does the loop do?",
         "Execute the pending tool(s), append tool_result, call again. Do not return to the user."),
        ("What is a valid safety brake but a bad primary stop condition?",
         "A max-iteration cap. Done is end_turn, not N turns."),
    ],
    "1.2": [
        ("When should the coordinator skip the full specialist pipeline?",
         "When the query is simple enough that the coordinator already has the facts or a smaller path is enough."),
        ("Subagents found a coverage gap in synthesis. Next step?",
         "Re-delegate with a targeted query, then synthesize again. Do not ship a one-pass incomplete report."),
    ],
    "1.3": [
        ("Coordinator has AgentDefinitions but never spawns. First check?",
         "allowedTools must include Task (or Agent). Definitions without that tool cannot launch."),
        ("How do you start two independent specialists with less latency?",
         "Emit multiple Task calls in one coordinator response, not one per turn."),
    ],
    "1.4": [
        ("Identity must be verified before refund. Prompt or code?",
         "Code: a gate, hook, or tool that refuses process_refund until get_customer succeeded."),
        ("What must an escalation packet contain?",
         "Ids, root cause, amounts, actions taken, recommended next step — not only the first complaint."),
    ],
    "1.5": [
        ("Three MCP tools return dates in different formats. Which hook?",
         "PostToolUse: normalize before the model reasons over the results."),
        ("Refunds over a threshold must never execute. Prompt or hook?",
         "Interception / PreToolUse (or enforce inside the tool). Prompts cannot guarantee it."),
    ],
    "1.6": [
        ("Billing dispute is always verify → invoice → policy → propose. Which pattern?",
         "Prompt chaining. The path is known and should stay consistent."),
        ("Next debug step depends on the last log line. Which pattern?",
         "Dynamic decomposition, with a termination rule so it cannot run forever."),
    ],
    "1.7": [
        ("You want two implementations from the same prior analysis. Resume twice?",
         "No. Fork the session (and isolate files if both will edit disk)."),
        ("Yesterday's tool results are about prices that changed overnight. Resume?",
         "Usually no. Fresh session plus a structured summary and new lookups."),
    ],
    "2.1": [
        ("analyze_content and analyze_document keep getting swapped. First fix?",
         "Rename/split and rewrite descriptions so when-to-use is mutually exclusive."),
        ("Why is dry_run: boolean a weak confirmation design?",
         "The model can pass false. Use preview plus a one-time token."),
    ],
    "2.2": [
        ("Calendar API 404 vs omitted required email. Which error tier?",
         "404 after a well-formed call is isError tool execution. Missing required param is protocol/JSON-RPC."),
        ("Payment send timed out after submit. Retryable?",
         "No. Uncertain write. Verify status or ask the user. Do not auto-retry."),
    ],
    "2.3": [
        ("Must extract JSON but document type is unknown. tool_choice?",
         "any — a tool must run, the model picks which extractor."),
        ("Synthesis agent keeps web-searching instead of writing. Fix?",
         "Remove search from its allowed tools; pass findings in the prompt."),
    ],
    "2.4": [
        ("Team needs a Jira server; you are testing a personal fork. Where do configs live?",
         "Shared: project .mcp.json. Personal experiment: local/user ~/.claude.json. Secrets via env vars."),
        ("Agent uses Grep instead of a richer MCP search. First lever?",
         "Improve the MCP tool description (when to prefer it, inputs, outputs). Do not immediately delete Grep."),
    ],
    "2.5": [
        ("Find every caller of refundOrder. Grep or Glob?",
         "Grep. Glob is path/name patterns, not file contents."),
        ("Edit fails because old_string matches twice. Next?",
         "Widen the unique anchor; if still not unique, Read then Write."),
    ],
    "3.1": [
        ("A new hire does not see the team's testing rules. Likely cause?",
         "Rules live in ~/.claude/CLAUDE.md (user), not project CLAUDE.md."),
        ("Is CLAUDE.md a guarantee the model will comply?",
         "No. It is context. Hard bans belong in hooks or permissions.deny. Use /memory to see what loaded."),
    ],
    "3.2": [
        ("A 400-line release checklist should not be in CLAUDE.md. What instead?",
         "A skill (or slash command if a human must invoke it). Use context: fork if output is huge."),
        ("Skill vs slash command?",
         "Skill: the task nature can load it. Slash command: a deliberate human button."),
    ],
    "3.3": [
        ("All *.test.tsx files share conventions but live in many folders. Mechanism?",
         "A .claude/rules file with a paths glob, not a nested CLAUDE.md in one test folder."),
        ("Why not put a code-review checklist in path rules?",
         "It would fire whenever those files are read, not only during review. That is task-scoped — use a command or skill."),
    ],
    "3.4": [
        ("45-file library migration. Plan or direct?",
         "Plan mode (then execute the agreed plan). Direct is for a narrow obvious edit."),
        ("Plan mode vs extended thinking?",
         "Plan mode is an approval gate. Thinking is reasoning budget. Different problems."),
    ],
    "3.5": [
        ("Two bugs interact; fixing one breaks the other. One message or sequential?",
         "One detailed message covering both. Sequential fixes will fight."),
        ("Same defect on every retry of the same prompt. What now?",
         "Change examples, schema, or criteria. Another blind retry will not generalize."),
    ],
    "3.6": [
        ("CI Claude Code hangs waiting for input. Missing flag?",
         "-p / --print for non-interactive mode."),
        ("Why not review in the same session that wrote the code?",
         "That context is biased toward its own plan. Use an independent instance and schema-shaped JSON."),
    ],
    "4.1": [
        ("Review bot says 'be conservative' and still nags about style. Better fix?",
         "Explicit report vs skip categories. Optionally disable the noisy category while you repair it."),
        ("Why do false positives in one category hurt the whole bot?",
         "Developers stop trusting even the accurate categories."),
    ],
    "4.2": [
        ("Format is inconsistent despite a long rule list. Highest-leverage add?",
         "Two to four complete examples, including the ambiguous case you actually fail."),
        ("Are examples only for exact matching?",
         "No. Contrast pairs teach generalization to novel but similar cases."),
    ],
    "4.3": [
        ("Downstream inserts JSON into a database. Prompt-only JSON keeps growing fences. Fix?",
         "Structured outputs or a forced extraction tool plus application validation."),
        ("Source often omits lot size. Required number field. What happens?",
         "The model is pressured to fabricate. Make the field nullable and show a null example."),
    ],
    "4.4": [
        ("Schema is valid but line items do not sum. Next request should include?",
         "The source, the failed extract, and the exact validation errors — not the same prompt again."),
        ("Fact lives only in a PDF you never sent. Retry?",
         "No. Retrieve the document or send to a human. Retry cannot invent the source."),
    ],
    "4.5": [
        ("Pre-merge test gate. Batch or real-time?",
         "Real-time. Batch has no low-latency SLA and no mid-request tool loop."),
        ("30h SLA, 24h batch window, 4h post-process. Max submit gap?",
         "2 hours. Worst case is miss-the-batch wait + 24 + 4."),
    ],
    "4.6": [
        ("Same chat writes code then 'reviews' it. Why is that weak?",
         "It still has the authoring rationale. Use a cold instance plus local then integration passes."),
        ("One pass over a 40-file PR. Risk?",
         "Attention dilution and contradictory findings. Split local vs cross-file."),
    ],
    "5.1": [
        ("Allergy stated on turn 3, session is turn 50. Sliding window doubled. Still safe?",
         "No. Keep allergies in a persistent reference / state object; do not rely on a longer window."),
        ("lookup_order returns 40 fields every turn. What crowds out the case?",
         "Uncompressed tool results. Keep the five fields you need."),
    ],
    "5.2": [
        ("User is angry but the credit is clearly allowed. Immediate escalate?",
         "No. Acknowledge, offer to finish now, keep their choice. Escalate if they still want a human or policy is silent."),
        ("Three 'Alex Smith' rows. Pick the newest?",
         "No. Ask for another identifier. Do not heuristic-guess a refund target."),
    ],
    "5.3": [
        ("Specialist times out. Coordinator sees 'unavailable'. What is missing?",
         "Failure type, query attempted, partial hits, alternatives. Generic status blocks recovery."),
        ("One source is down. Kill the whole research workflow?",
         "No. Continue with partials and annotate the coverage gap."),
    ],
    "5.4": [
        ("After 80 turns the model cites 'typical service patterns' instead of PaymentService.",
         "Context decay. Persist a scratchpad and reread it; delegate verbose grepping to a subagent."),
        ("Crash mid-exploration. Replay every tool payload?",
         "No. Load a structured manifest and inject only the relevant slice."),
    ],
    "5.5": [
        ("Pipeline is 96.5% accurate. Auto-approve high confidence now?",
         "Not until you segment by document type/field and calibrate scores. Then keep stratified sampling."),
        ("Model says confidence 0.92. Is that 92% accurate?",
         "Only after you measure it on labeled data. Uncalibrated scores are not a gate."),
    ],
    "5.6": [
        ("Two credible sources disagree on a percentage. Pick the newer one?",
         "No. Keep both with attribution and dates. Mark the finding contested."),
        ("Report writer got only an executive summary and must cite. Why will it fail?",
         "Citations died in the summary. Pass claim–source–date records."),
    ],
}


def checks_html(tid: str) -> str:
    items = CHECKS.get(tid, [])
    if not items:
        return ""
    blocks = []
    for i, (q, a) in enumerate(items, 1):
        blocks.append(
            f'<div class="check" data-task="{html.escape(tid)}" data-n="{i}">'
            f"<p><strong>Q{i}.</strong> {html.escape(q)}</p>"
            f'<button type="button" class="btn btn-reveal reveal">Show answer</button>'
            f'<div class="answer hidden"><p>{html.escape(a)}</p></div>'
            f'<div class="grade hidden">'
            f'<button type="button" class="btn btn-warn miss">Missed</button>'
            f"</div></div>"
        )
    return (
        '<h3>Self-check</h3><p class="meta">Reveal the answer, then mark Missed if you would have gotten it wrong. Those items show up more often in Drill.</p>'
        + "".join(blocks)
    )


TASK_META = {
    "1.1": {
        "title": "Agentic loops",
        "intro": """
<h3>Definition</h3>
<p>An agentic application is a control loop around Claude. The model proposes the next action; your code inspects the API signal, executes tools, appends results, and calls again until the model is finished. This is not a single request-response. It is not a hard-coded decision tree unless you deliberately build one.</p>
<p>Claude's Messages API is stateless. Claude does not remember previous API calls unless your application includes the relevant content in the next request. A <code>session_id</code> in your product, database, or orchestration layer can help you find stored history, but the model only sees what the request contains.</p>
<h3>How the loop works</h3>
<pre>send request (system + messages + tools)
inspect stop_reason
  tool_use  → execute each tool_use block
            → append tool_result blocks on a user turn
            → send the updated conversation again
  end_turn  → stop and return the assistant reply
  max_tokens / refusal / context overflow → handle that signal; do not pretend the turn completed</pre>
<p>Tool use is represented with content blocks: assistant messages can contain <code>tool_use</code> blocks, and user messages can contain <code>tool_result</code> blocks. The system prompt belongs in the top-level <code>system</code> parameter, not as a <code>"system"</code> role inside <code>messages</code>.</p>
<h3>Model-driven vs pre-configured flow</h3>
<p>In a true agent loop, Claude reasons about which tool to call next from context. That is different from a pre-configured decision tree or a forced tool sequence. Forced sequences are valid when the workflow is fixed (prompt chaining or a programmatic gate). They are the wrong mental model for "the agent decides."</p>
<h3>Anti-patterns this task exists to catch</h3>
<ul>
<li>Parsing natural language ("I'm done", "Refund processed") to decide loop termination.</li>
<li>Checking for assistant text content as a completion indicator while <code>stop_reason</code> is still <code>tool_use</code>.</li>
<li>Using an arbitrary iteration cap as the primary stopping mechanism. Caps are a safety brake against runaway cost, not the definition of done.</li>
<li>Forgetting to append tool results, then wondering why the model repeats the same call or "forgets" the refund happened.</li>
</ul>
""",
        "skills": [
            "Continue the loop when stop_reason is tool_use; terminate when it is end_turn.",
            "Add tool results to conversation context between iterations.",
            "Avoid prose-parsing, text-presence checks, and iteration caps as the main completion logic.",
        ],
        "chapters": [
            "1. API Fundamentals and Output Control",
            "8. Agentic Patterns and Task Decomposition",
            "12. Model Selection and Inference Controls",
        ],
    },
    "1.2": {
        "title": "Coordinator–subagent orchestration",
        "intro": """
<h3>Definition</h3>
<p>Hub-and-spoke architecture: a coordinator manages inter-subagent communication, error handling, and information routing. Subagents operate with isolated context. They do not inherit the coordinator's conversation history automatically.</p>
<p>The coordinator's job is task decomposition, delegation, result aggregation, and deciding which specialists to invoke based on query complexity. Overly narrow decomposition leaves holes in broad research. Always running the full pipeline wastes cost on simple facts.</p>
<h3>How it works</h3>
<p>The coordinator analyzes the query and dynamically selects subagents. It partitions research scope (distinct subtopics or source types) to minimize duplication. After synthesis, it evaluates coverage. If there are gaps, it re-delegates with targeted queries and re-invokes synthesis until coverage is sufficient.</p>
<p>All subagent communication goes through the coordinator. That gives observability, consistent error handling, and controlled information flow. Subagents should not message each other.</p>
<h3>When not to delegate</h3>
<p>Each delegation costs a tool call, a fresh context, a separate model invocation, and a result-passing step. If the coordinator already has the relevant context and the work is small, do the work in the coordinator's turn.</p>
""",
        "skills": [
            "Design coordinators that choose a smaller path for simple queries.",
            "Partition research to minimize duplication.",
            "Run iterative refinement when synthesis finds gaps.",
            "Route all specialist communication through the hub.",
        ],
        "chapters": ["8. Agentic Patterns and Task Decomposition"],
    },
    "1.3": {
        "title": "Subagent invocation and context passing",
        "intro": """
<h3>Definition</h3>
<p>The Task tool (sometimes named Agent) is how a coordinator spawns subagents. The parent's <code>allowedTools</code> must include that tool or delegation silently fails: definitions exist, but there is no callable interface.</p>
<p>Subagent context must be explicitly provided in the prompt. Subagents do not automatically inherit parent context or share memory between invocations. Each <code>AgentDefinition</code> has a description, system prompt, and tool restrictions.</p>
<h3>How to pass context</h3>
<p>Include complete findings from prior agents in the next agent's prompt. Use structured formats that separate content from metadata (source URLs, document names, page numbers) so attribution survives. For final reports that need citations, do not pass only a prose summary — pass a claim–source index.</p>
<p>Spawn parallel subagents by emitting multiple Task tool calls in a single coordinator response, not across separate turns. Coordinator prompts should specify research goals and quality criteria rather than brittle step-by-step search strings when adaptability matters.</p>
<p>A second invocation of the "same" subagent is a new agent. Persist an identifier or summary in the parent and re-supply it. Fork-based session management explores divergent approaches from a shared analysis baseline without overwriting the original transcript.</p>
""",
        "skills": [
            "Include Task/Agent in the coordinator's allowedTools.",
            "Pass complete prior findings and structured metadata into each subagent prompt.",
            "Emit multiple Task calls in one turn for independent work.",
            "Give goals and quality criteria, not over-prescribed search strings, when the specialist must adapt.",
        ],
        "chapters": [
            "8. Agentic Patterns and Task Decomposition",
            "10. Claude Code and Claude Agent SDK Workflows",
        ],
    },
    "1.4": {
        "title": "Enforcement and handoff patterns",
        "intro": """
<h3>Definition</h3>
<p>Programmatic enforcement (hooks, prerequisite gates, tool-level policy) is different from prompt-based guidance. When deterministic compliance is required — identity verification before financial operations — prompt instructions alone have a non-zero failure rate.</p>
<h3>How it works</h3>
<p>Implement programmatic prerequisites that block downstream tool calls until prerequisite steps have completed (for example, block <code>process_refund</code> until <code>get_customer</code> has returned a verified customer ID). Decompose multi-concern customer requests into distinct items, investigate each in parallel using shared context, then synthesize a unified resolution.</p>
<p>When escalating mid-process, compile a structured handoff: customer ID, root cause, amounts, records, actions taken, recommended next action. The receiving human often lacks the conversation transcript. Do not pass only the first complaint. Do not dump an unusable full transcript unless the receiving system can use it.</p>
<p>The safest design often puts the rule inside the tool itself. Thresholds come from server-controlled state (policy service, account record), not from a model-supplied <code>override=true</code> parameter.</p>
""",
        "skills": [
            "Block downstream tools until prerequisites succeed.",
            "Split multi-concern requests, investigate, then synthesize.",
            "Produce structured escalation packets, not raw chat dumps.",
        ],
        "chapters": ["9. Customer Service and Production Workflow Design"],
    },
    "1.5": {
        "title": "Agent SDK hooks",
        "intro": """
<h3>Definition</h3>
<p>Hooks intercept the agent loop at lifecycle events. They provide deterministic guarantees. Prompt instructions provide probabilistic guidance. Choose hooks when a business rule must hold every time.</p>
<h3>How it works</h3>
<p><code>PostToolUse</code> intercepts tool results for transformation before the model processes them — for example, normalizing Unix timestamps, ISO 8601 dates, and numeric status codes from different MCP tools into one schema.</p>
<p>Interception hooks on the way out enforce compliance: block refunds above a threshold and redirect to human escalation. In Claude Code, <code>PreToolUse</code> can deny, allow, ask the user, defer to normal permissions, inject context, or modify tool input. That is the right class of mechanism for "must always require approval."</p>
<p>Other hooks: <code>UserPromptSubmit</code> (block or enrich a user prompt), <code>SessionStart</code> (load project context). Hooks execute as code in your environment — shell commands in Claude Code, callbacks in the Agent SDK. Review third-party hook configs like any other code you run.</p>
<p><code>CLAUDE.md</code> is soft guidance. Hooks and <code>permissions.deny</code> are hard enforcement.</p>
""",
        "skills": [
            "Use PostToolUse to normalize heterogeneous tool results.",
            "Use interception to block policy-violating actions and redirect.",
            "Choose hooks over prompts when compliance must be guaranteed.",
        ],
        "chapters": ["10. Claude Code and Claude Agent SDK Workflows", "15. Security and Trust Boundaries"],
    },
    "1.6": {
        "title": "Task decomposition",
        "intro": """
<h3>Definition</h3>
<p>The decision is not "which pattern is best." It is "which pattern matches the shape of this work."</p>
<h3>How it works</h3>
<p><strong>Prompt chaining</strong> breaks work into sequential focused steps. Use it when steps are known and stable: a three-stage review (style, then security, then docs), or a billing dispute that always runs verify identity → fetch invoice → check policy → propose adjustment.</p>
<p><strong>Dynamic / adaptive decomposition</strong> generates the next subtask from what was just learned. Use it for investigations: intermittent backend failures, unusual customer errors, flaky tests. A pre-written checklist either misses the cause or wastes effort. Dynamic plans need termination criteria and step caps because they are harder to budget.</p>
<p>Large code reviews should split into per-file local analysis plus a separate cross-file integration pass so attention is not diluted and findings do not contradict each other.</p>
<p>Open-ended work such as "add comprehensive tests to a legacy codebase" should start by mapping structure, identifying high-impact areas, then creating a prioritized plan that adapts as dependencies are discovered.</p>
""",
        "skills": [
            "Select chaining for predictable multi-aspect reviews and dynamic decomposition for investigations.",
            "Split large reviews into local passes plus an integration pass.",
            "Map first, then prioritize, for open-ended legacy work.",
        ],
        "chapters": ["8. Agentic Patterns and Task Decomposition"],
    },
    "1.7": {
        "title": "Sessions, resume, and fork",
        "intro": """
<h3>Definition</h3>
<p>Sessions persist conversation history, not filesystem state. Resume continues a transcript. Fork copies a transcript into an independent branch. Starting fresh with a structured summary is more reliable than resuming when prior tool results are stale.</p>
<h3>How it works</h3>
<table>
<tr><th>Control</th><th>Behavior</th><th>Use</th></tr>
<tr><td><code>--continue</code></td><td>Most recent conversation in this directory</td><td>You are sure "latest" is the right work</td></tr>
<tr><td><code>--resume</code> / named session</td><td>A specific saved session</td><td>Return to a known investigation</td></tr>
<tr><td><code>--session-id</code></td><td>Stable UUID</td><td>Programmatic workflows</td></tr>
<tr><td>fork / <code>--fork-session</code></td><td>Independent branch from a baseline</td><td>Compare two testing or refactoring approaches</td></tr>
</table>
<p>If the codebase changed: resume and tell Claude exactly which files changed when most prior context remains useful. Start fresh with a summary when the old transcript is likely stale or misleading. Do not only add "prefer the most recent tool results" — models still latch onto richer older payloads.</p>
<p>Fork the session and isolate files (git worktree) if two implementations must not collide on disk. Do not resume the same session from two terminals. The same session that wrote code is weaker at reviewing it — use a fresh review context.</p>
<p>Long multi-agent workflows should persist structured manifests (completed steps, document ids, open gaps) and inject only relevant slices on resume.</p>
""",
        "skills": [
            "Use named resume for a specific investigation.",
            "Use fork to explore divergent approaches from a shared baseline.",
            "Choose resume vs fresh-plus-summary based on whether old tool results are still valid.",
            "Tell a resumed session exactly what changed instead of forcing a full re-exploration.",
        ],
        "chapters": ["10. Claude Code and Claude Agent SDK Workflows", "5. Conversation Context Management"],
    },
    "2.1": {
        "title": "Effective tool interfaces",
        "intro": """
<h3>Definition</h3>
<p>Tool descriptions are the primary mechanism models use for tool selection. Minimal or overlapping descriptions cause misrouting. Tool design is prompt design plus API design: a good interface makes the right action easy and the wrong action difficult or impossible.</p>
<h3>How it works</h3>
<p>Write descriptions that state purpose, expected inputs, outputs, when to use the tool, and when to use a similar alternative instead. Include input formats, example queries, edge cases, and boundaries. Rename tools that collide (<code>analyze_content</code> vs <code>analyze_document</code>). Split generic tools into purpose-specific contracts (<code>extract_data_points</code>, <code>summarize_content</code>, <code>verify_claim_against_source</code>).</p>
<p>Keyword-sensitive system prompts can create unintended tool associations. Audit both the prompt and the descriptions.</p>
<p>Parameter design: enums for closed sets; lookup-then-act for ambiguous names; stable IDs in downstream tools; split tools when required fields differ by operation. Compose only mechanical or race-prone sequences (find-and-book). Keep judgment steps separate.</p>
<p>Do not use a model-controlled <code>dry_run</code> boolean for mandatory confirmation. Use preview plus a one-time token. Empty search is success with an empty array, not an error. Large catalogs need progressive discovery, not one <code>find_and_execute</code> mega-tool.</p>
""",
        "skills": [
            "Write descriptions that differentiate similar tools.",
            "Rename or split overlapping tools.",
            "Review system prompts for keyword associations that override descriptions.",
        ],
        "chapters": ["2. Designing Tool Interfaces for LLM Agents"],
    },
    "2.2": {
        "title": "Structured MCP errors",
        "intro": """
<h3>Definition</h3>
<p>Uniform errors ("Operation failed") prevent the agent from making recovery decisions. Production tools classify failures and return enough context for retry, correction, user explanation, or escalation.</p>
<h3>How it works</h3>
<p>MCP has two error tiers. Protocol / JSON-RPC errors mean the call was not a well-formed invocation (missing required parameter, unknown method). Tool execution errors use <code>isError: true</code> when the tool ran but the operation failed (404, 503, denied, business rule).</p>
<p>Categories: transient (retry inside the tool on safe reads), validation (return field details so the model can correct), business (non-retryable + customer explanation), permission (non-retryable + escalation path), uncertain write (timeout after submit — do not auto-retry).</p>
<p>Subagents should recover locally from transients and propagate to the coordinator only errors they cannot resolve, plus partial results and what was attempted. Distinguish access failures from valid empty results.</p>
""",
        "skills": [
            "Return errorCategory, isRetryable, and a human-readable description.",
            "Mark business violations non-retryable with a customer-facing explanation.",
            "Recover transients inside the subagent; escalate structured partial failures.",
            "Never treat 'no matches' as a tool failure.",
        ],
        "chapters": ["3. Error Handling in Agent Tools"],
    },
    "2.3": {
        "title": "Tool distribution and tool_choice",
        "intro": """
<h3>Definition</h3>
<p>Giving an agent too many tools degrades selection. Agents with tools outside their specialization misuse them. Scoped access means each agent gets only what its role needs, plus maybe one narrow cross-role tool for a high-frequency need.</p>
<h3>How tool_choice works</h3>
<table>
<tr><th>Setting</th><th>Meaning</th><th>Use</th></tr>
<tr><td><code>auto</code></td><td>May call a tool or answer</td><td>General agents</td></tr>
<tr><td><code>any</code></td><td>Must call one of the provided tools</td><td>Unknown document type; extraction must happen</td></tr>
<tr><td>named tool</td><td>Must call that tool</td><td>Metadata extraction before enrichment</td></tr>
<tr><td><code>none</code></td><td>No tools</td><td>Pure text or an unsafe step</td></tr>
</table>
<p><code>auto</code> plus a prompt that says "use a tool" can still produce conversation. <code>any</code> cannot. Force the first required tool, then continue in later turns. Do not rely on tool-list order or prompt priority.</p>
""",
        "skills": [
            "Restrict each subagent's tools to its role.",
            "Replace generic tools with constrained alternatives when needed.",
            "Use forced tool_choice for a required first step; use any when a tool call must happen but the schema is not yet known.",
        ],
        "chapters": [
            "1. API Fundamentals and Output Control",
            "2. Designing Tool Interfaces for LLM Agents",
            "8. Agentic Patterns and Task Decomposition",
        ],
    },
    "2.4": {
        "title": "MCP servers in Claude Code",
        "intro": """
<h3>Definition</h3>
<p>MCP is an open standard: servers expose tools, resources, and prompts; hosts decide how models use them. MCP does not automatically handle auth, retries, rate limits, or authorization.</p>
<h3>How configuration works</h3>
<table>
<tr><th>Scope</th><th>Storage</th><th>Who sees it</th></tr>
<tr><td>Project</td><td><code>.mcp.json</code> at repo root</td><td>The team, via version control</td></tr>
<tr><td>Local</td><td><code>~/.claude.json</code> keyed to this project path</td><td>Only you, this project</td></tr>
<tr><td>User</td><td><code>~/.claude.json</code> global</td><td>Only you, every project</td></tr>
</table>
<p>Same-name servers resolve local &gt; project &gt; user. The winning definition is used whole, not merged. Expand credentials with environment variables such as <code>${GITHUB_TOKEN}</code>; do not commit secrets.</p>
<p>Tools from all connected servers are discovered and available together. If the agent prefers Grep over a stronger MCP tool, improve the MCP description. Prefer community servers for standard SaaS; write custom servers for team-specific workflows.</p>
<p>Resources expose content catalogs (issue summaries, documentation trees, database schemas) so the agent does not burn exploratory tool calls. Annotations such as <code>readOnlyHint</code> are untrusted hints, not a security boundary.</p>
""",
        "skills": [
            "Put shared servers in project .mcp.json with env-var credentials.",
            "Put personal/experimental servers in user or local ~/.claude.json.",
            "Write descriptions that win against built-in tools when the MCP tool is stronger.",
            "Expose catalogs as resources.",
        ],
        "chapters": ["7. Model Context Protocol (MCP)"],
    },
    "2.5": {
        "title": "Built-in tools",
        "intro": """
<h3>Definition</h3>
<p>Pick the tool that matches the question. Using the wrong built-in tool is a common exam distinction.</p>
<table>
<tr><th>Need</th><th>Tool</th></tr>
<tr><td>Search file contents (functions, errors, imports)</td><td>Grep</td></tr>
<tr><td>Find files by name or path pattern</td><td>Glob</td></tr>
<tr><td>Read a known file</td><td>Read</td></tr>
<tr><td>Targeted unique edit</td><td>Edit / MultiEdit</td></tr>
<tr><td>Edit cannot find unique anchor text, or full rewrite</td><td>Read then Write</td></tr>
<tr><td>Tests and shell commands</td><td>Bash</td></tr>
<tr><td>Broad isolated exploration</td><td>Task / Explore subagent</td></tr>
</table>
<h3>How to explore a codebase</h3>
<p>Start from entry points. Grep for route names, error codes, or function identifiers. Read matching files. Follow imports. Trace one or two representative paths. Do not read hundreds of files upfront. To trace wrappers: identify exported names, then Grep each name.</p>
<p>When asking Claude Code to follow project patterns, point at concrete files rather than "follow our usual style."</p>
""",
        "skills": [
            "Choose Grep for content and Glob for paths.",
            "Fall back to Read + Write when Edit is not unique.",
            "Build understanding incrementally instead of reading the tree.",
        ],
        "chapters": ["10. Claude Code and Claude Agent SDK Workflows"],
    },
    "3.1": {
        "title": "CLAUDE.md hierarchy",
        "intro": """
<h3>Definition</h3>
<p><code>CLAUDE.md</code> and rule files are persistent context, not enforced configuration. The model tries to follow them. There is no compliance guarantee. Hard rules belong in hooks or <code>permissions.deny</code>.</p>
<h3>How loading works</h3>
<table>
<tr><th>Scope</th><th>Location</th><th>Shared with the team?</th></tr>
<tr><td>Managed policy</td><td>OS-specific policy path</td><td>Organization-wide; cannot be excluded</td></tr>
<tr><td>User</td><td><code>~/.claude/CLAUDE.md</code></td><td>No</td></tr>
<tr><td>Project</td><td><code>./CLAUDE.md</code> or <code>./.claude/CLAUDE.md</code></td><td>Yes — commit it</td></tr>
<tr><td>Local</td><td><code>CLAUDE.local.md</code></td><td>No — gitignore</td></tr>
</table>
<p>Broader scopes load first; more specific last. Ancestor files load fully at launch. Subdirectory files load on demand when that subtree is read. <code>@imports</code> organize content but still consume tokens at launch (up to five hops). <code>/memory</code> shows what is actually loaded — use it before rewriting instructions.</p>
<p>If a new teammate "does not get the rules," the instructions are probably in user-level memory, not project CLAUDE.md.</p>
""",
        "skills": [
            "Diagnose hierarchy issues (user vs project).",
            "Use @import to keep files modular.",
            "Split large files into .claude/rules/ by topic.",
            "Verify loaded files with /memory.",
        ],
        "chapters": ["10. Claude Code and Claude Agent SDK Workflows"],
    },
    "3.2": {
        "title": "Slash commands and skills",
        "intro": """
<h3>Definition</h3>
<p>Slash commands are human-invoked reusable prompts. Skills are on-demand procedures Claude can also self-select from a short description. CLAUDE.md is always-on facts. Hooks are hard enforcement.</p>
<h3>How they work</h3>
<p>Project commands live in <code>.claude/commands/</code> and are shared. User commands live in <code>~/.claude/commands/</code>. Skills live in a folder with <code>SKILL.md</code>. The description stays in context; the body loads when the task matches. That progressive disclosure is the point of a long release checklist.</p>
<p>Frontmatter: <code>context: fork</code> runs the skill in an isolated sub-agent so verbose analysis does not pollute the main conversation. <code>allowed-tools</code> restricts tools during the skill. <code>argument-hint</code> prompts for missing parameters. Personal variants go in <code>~/.claude/skills/</code> under a different name so teammates are unaffected.</p>
<p>Prefer a skill when the nature of the task should trigger the procedure. Prefer a slash command when invocation must remain a deliberate human act.</p>
""",
        "skills": [
            "Create project-scoped commands for team workflows.",
            "Use context: fork for verbose or exploratory skills.",
            "Restrict allowed-tools on skills that must not be destructive.",
            "Use argument-hint when invocation needs parameters.",
            "Choose skills vs CLAUDE.md based on always-on vs on-demand.",
        ],
        "chapters": ["10. Claude Code and Claude Agent SDK Workflows"],
    },
    "3.3": {
        "title": "Path-specific rules",
        "intro": """
<h3>Definition</h3>
<p><code>.claude/rules/</code> files with YAML <code>paths</code> globs load only when matching files are read. That reduces irrelevant context. Globs beat subdirectory CLAUDE.md when the same convention applies across the tree (all <code>*.test.tsx</code> files).</p>
<h3>How it works</h3>
<p>A rule with no <code>paths</code> loads unconditionally like project CLAUDE.md. Personal rules can live in <code>~/.claude/rules/</code>. Project rules win where they overlap.</p>
<p>Do not use path rules for task-scoped checklists such as code review. Those fire whenever matching files are touched, not only during a review. Task-scoped work belongs in a command, skill, or subagent.</p>
""",
        "skills": [
            "Write paths globs so rules load only for matching files.",
            "Use globs for conventions that span directories.",
            "Choose path rules over nested CLAUDE.md when files are scattered.",
        ],
        "chapters": ["10. Claude Code and Claude Agent SDK Workflows"],
    },
    "3.4": {
        "title": "Plan mode vs direct execution",
        "intro": """
<h3>Definition</h3>
<p>Plan mode is workflow control: read-only exploration, a proposed plan, human approval, then edits. Direct execution is for simple, well-scoped changes. Extended thinking is a different mechanism — more internal reasoning budget, not an approval gate.</p>
<h3>How to choose</h3>
<p>Plan mode: large-scale changes, multiple valid approaches, architectural decisions, multi-file modifications, migrations, stakeholder approval. Direct execution: a single validation check, a one-file bug with a clear stack trace.</p>
<p>Use the Explore subagent to isolate verbose discovery and return summaries so the main conversation is not exhausted. You can plan the migration, then execute the agreed approach.</p>
<p>If the agent jumps to edits without surfacing trade-offs, use plan mode. If analyses are shallow on a hard problem, raise thinking effort. Both can be used together.</p>
""",
        "skills": [
            "Select plan mode for architectural or multi-file work.",
            "Select direct execution for narrow, obvious edits.",
            "Use Explore to keep discovery out of the main context.",
            "Combine plan-then-execute when investigation and implementation are different phases.",
        ],
        "chapters": ["10. Claude Code and Claude Agent SDK Workflows", "12. Model Selection and Inference Controls"],
    },
    "3.5": {
        "title": "Iterative refinement",
        "intro": """
<h3>Definition</h3>
<p>Concrete input/output examples and failing tests beat prose. Claude improves fastest when feedback is executable.</p>
<h3>How it works</h3>
<p>Write tests or 2–3 examples first. Ask for the smallest useful implementation. Run tests. Feed exact failures (input, expected, actual, assertion). Iterate one failure class at a time unless issues interact — then send them in one detailed message because sequential fixes will fight each other.</p>
<p>The interview pattern: have Claude ask questions to surface cache invalidation, failure modes, or auth decisions before implementing in an unfamiliar domain.</p>
<p>When the same defect recurs across runs, change the prompt, schema, or examples. Per-instance retries do not generalize. Generated tests that only assert "does not throw" are low value — document fixtures and behavioral standards.</p>
""",
        "skills": [
            "Use 2–3 input/output examples when prose is interpreted inconsistently.",
            "Drive iteration from real test failures.",
            "Use the interview pattern before implementing in unfamiliar domains.",
            "Batch interacting issues; sequence independent ones.",
        ],
        "chapters": ["11. Iterative Refinement, Testing, and Evaluation"],
    },
    "3.6": {
        "title": "Claude Code in CI/CD",
        "intro": """
<h3>Definition</h3>
<p>CI needs non-interactive, machine-readable, isolated review. A chat session attached to the authoring context is the wrong quality gate.</p>
<h3>How it works</h3>
<p>Use <code>-p</code> / <code>--print</code> so the process cannot hang on interactive input. Use <code>--output-format json</code> and <code>--json-schema</code> so findings can be posted as inline PR comments. Project CLAUDE.md supplies testing standards, fixture conventions, and review criteria to the CI-invoked process.</p>
<p>The same session that generated code is less effective at reviewing it. Use an independent instance. When re-running after new commits, include prior findings and instruct Claude to report only new or still-unaddressed issues. Provide existing tests so generation does not duplicate coverage.</p>
""",
        "skills": [
            "Run Claude Code in CI with -p.",
            "Emit schema-constrained JSON for automation.",
            "Avoid duplicate PR comments on re-review.",
            "Ground test generation in existing tests and CLAUDE.md standards.",
        ],
        "chapters": [
            "10. Claude Code and Claude Agent SDK Workflows",
            "11. Iterative Refinement, Testing, and Evaluation",
        ],
    },
    "4.1": {
        "title": "Explicit criteria",
        "intro": """
<h3>Definition</h3>
<p>Explicit criteria beat vague instructions. "Flag comments only when claimed behavior contradicts actual code behavior" is a criterion. "Check that comments are accurate" is not. "Be conservative" and "only report high-confidence findings" do not raise precision the way categorical rules do.</p>
<p>High false-positive categories undermine trust in accurate categories. Temporarily disable the noisy category while you improve its prompt, rather than letting it poison the whole bot.</p>
""",
        "skills": [
            "Define what to report vs skip, not just a confidence filter.",
            "Disable high false-positive categories while repairing them.",
            "Define severity with concrete examples per level.",
        ],
        "chapters": [
            "6. System Prompt Engineering and Conversational Behavior",
            "11. Iterative Refinement, Testing, and Evaluation",
        ],
    },
    "4.2": {
        "title": "Few-shot prompting",
        "intro": """
<h3>Definition</h3>
<p>Few-shot examples are usually the most effective way to get consistent format, handle ambiguous cases, and teach extraction from varied layouts. Two to four targeted examples beat a long rule list for subtle distinctions.</p>
<h3>How to write them</h3>
<p>Show complete input–output pairs. Show why one action was chosen over a plausible alternative. Show the exact output shape (location, issue, severity, suggested fix). Show acceptable code next to a genuine defect so the model generalizes instead of matching only listed cases. Show informal measurements extracted verbatim. Show inline citations versus bibliographies.</p>
<p>When the same defect keeps recurring, add an example of the correct handling. That generalizes; another retry of the same prompt does not.</p>
""",
        "skills": [
            "Write 2–4 examples for the actual ambiguous cases you fail.",
            "Demonstrate format, not only prose rules.",
            "Use contrast pairs to cut false positives without blocking novel true positives.",
        ],
        "chapters": [
            "4. Structured Data Extraction and Validation",
            "6. System Prompt Engineering and Conversational Behavior",
        ],
    },
    "4.3": {
        "title": "Structured output and schemas",
        "intro": """
<h3>Definition</h3>
<p>Tool use with a JSON schema is the reliable way to get schema-shaped output. Prompt-only "respond with JSON" still produces fences, commentary, and drift. Schema compliance eliminates many syntax errors; it does not prevent semantic errors (line items that do not sum, values in the wrong field).</p>
<p>Use JSON structured outputs (<code>output_config.format</code>) when the assistant's direct reply should be JSON. Use tool use when the structured object is a function call or extraction step. Assistant prefill to force <code>{</code> is legacy on current models.</p>
<h3>Schema design</h3>
<p>Make fields optional or nullable when the source may omit them — required fields pressure fabrication. Distinguish <code>null</code> (not stated) from <code>[]</code> (asked and found none). Add <code>unclear</code> or <code>other</code> plus a detail string for evolving categories. Include format-normalization rules in the prompt alongside the schema.</p>
""",
        "skills": [
            "Define an extraction tool and read structured data from tool_use.input.",
            "Use tool_choice any when document type is unknown; force a named tool for a required first stage.",
            "Design nullable fields and other+detail enums so the model can be honest.",
        ],
        "chapters": [
            "1. API Fundamentals and Output Control",
            "4. Structured Data Extraction and Validation",
        ],
    },
    "4.4": {
        "title": "Validation and feedback loops",
        "intro": """
<h3>Definition</h3>
<p>Retry-with-error-feedback: send the source, the failed extraction, and the exact validation errors. Blind retry of the same prompt is a weaker move. <code>temperature: 0</code> is not a substitute.</p>
<p>Retries fix format and structural mismatches. They cannot invent facts that exist only in a document you never provided — retrieve or send to a human.</p>
<p>Add reconciliation fields (<code>stated_total</code>, <code>calculated_total</code>, <code>conflict_detected</code>). For review agents, add <code>detected_pattern</code> so dismissed findings become prompt improvements.</p>
""",
        "skills": [
            "Implement follow-up requests that include document + failed output + errors.",
            "Recognize when retry cannot help.",
            "Instrument findings so false-positive patterns are visible.",
        ],
        "chapters": ["4. Structured Data Extraction and Validation", "11. Iterative Refinement, Testing, and Evaluation"],
    },
    "4.5": {
        "title": "Batch processing",
        "intro": """
<h3>Definition</h3>
<p>The Message Batches API is about 50% cheaper and can take up to 24 hours. There is no guaranteed low-latency SLA. Results are unordered — join by <code>custom_id</code>. A batch request cannot run a multi-turn tool loop inside a single item.</p>
<p>Appropriate: overnight reports, weekly audits, nightly test generation. Inappropriate: blocking pre-merge checks and anything a user is waiting on.</p>
<h3>SLA cadence</h3>
<p>Worst case ≈ time until the next submission + batch window (up to 24h) + post-processing. If the SLA is 30 hours and post-processing is 4 hours, cadence can be at most 2 hours. A single midnight batch misses documents that arrive just after submission.</p>
<p>Resubmit only failed ids. Chunk context-length failures. Sample and refine prompts before a huge first batch when you expect iteration. Official exam scope: know that prompt caching exists; you do not need caching implementation internals.</p>
""",
        "skills": [
            "Match real-time vs batch to latency requirements.",
            "Calculate submission frequency from SLA − 24h − processing buffer.",
            "Resubmit only failed custom_id records, with chunking or prompt fixes as needed.",
        ],
        "chapters": ["14. Batch Processing, Cost, and Latency", "13. Prompt Caching"],
    },
    "4.6": {
        "title": "Multi-instance and multi-pass review",
        "intro": """
<h3>Definition</h3>
<p>A model retains reasoning context from generation, so it is less likely to question its own decisions in the same session. An independent instance without that context is more effective than self-review instructions or extended thinking in the authoring chat.</p>
<p>Multi-pass review: per-file local analysis plus a separate cross-file integration pass. That avoids attention dilution and contradictory findings on large PRs.</p>
""",
        "skills": [
            "Use a second Claude instance to review generated code.",
            "Split large reviews into local plus integration passes.",
            "Optionally emit calibrated confidence for routing humans — after you measure it.",
        ],
        "chapters": [
            "8. Agentic Patterns and Task Decomposition",
            "10. Claude Code and Claude Agent SDK Workflows",
            "11. Iterative Refinement, Testing, and Evaluation",
        ],
    },
    "5.1": {
        "title": "Preserving critical context",
        "intro": """
<h3>Definition</h3>
<p>Context management is state management. The model sees a request, not your database. A large window is not the same as attention: models process beginnings and ends more reliably than middles (lost-in-the-middle). Progressive summaries blur numbers, dates, and customer-stated expectations if you let them.</p>
<h3>How to preserve the right things</h3>
<p>Extract transactional facts (amounts, dates, order numbers, statuses) into a persistent case-facts block included in every prompt, outside the summarized history. For multi-issue sessions, keep structured issue state per item. Trim verbose tool outputs to the fields that matter before they accumulate. Place key findings at the beginning of aggregated inputs and section-header the rest.</p>
<p>You must send the conversation you want remembered. There is no magic memory flag. API compaction and context editing can keep a long session alive; application-level structured state controls what must survive verbatim.</p>
""",
        "skills": [
            "Keep exact facts in a structured block, not only in a prose summary.",
            "Compress tool results before they dominate context.",
            "Order aggregated inputs to mitigate position effects.",
            "Require dates, sources, and method notes in specialist outputs.",
        ],
        "chapters": ["5. Conversation Context Management"],
    },
    "5.2": {
        "title": "Escalation and ambiguity",
        "intro": """
<h3>Definition</h3>
<p>Escalate when the customer explicitly wants a human (honor immediately if you cannot finish without overriding them), when policy is silent or requires an exception, when you cannot make meaningful progress, or when state is uncertain/unsafe. Do not escalate on a turn counter, sentiment score, or uncalibrated self-confidence.</p>
<p>If the issue is straightforward and the user is frustrated, acknowledge the frustration and offer to finish now while preserving their choice. Do not silently take account actions after they asked for a person.</p>
<p>Multiple customer matches require another identifier, not a heuristic pick. Ask one focused clarifying question when the action is high impact. State assumptions when risk is low. Surface conflicting goals; do not average them.</p>
""",
        "skills": [
            "Put explicit escalation criteria and few-shot examples in the prompt.",
            "Honor explicit human requests; offer resolution when the case is simple and they are frustrated.",
            "Escalate policy gaps instead of inventing policy.",
            "Clarify ambiguous entity matches instead of guessing.",
        ],
        "chapters": [
            "9. Customer Service and Production Workflow Design",
            "6. System Prompt Engineering and Conversational Behavior",
        ],
    },
    "5.3": {
        "title": "Error propagation in multi-agent systems",
        "intro": """
<h3>Definition</h3>
<p>Structured error context (failure type, attempted query, partial results, alternatives) lets the coordinator recover. Generic "search unavailable" hides that context. Silently turning failures into empty success, or killing the whole workflow on one specialist failure, are both wrong.</p>
<p>Access failures (timeouts) need retry decisions. Valid empty results are successful queries with no matches. Subagents retry transients locally and propagate only what they cannot fix. Synthesis should annotate coverage: well-supported versus gaps because a source was down.</p>
""",
        "skills": [
            "Return structured failure context with partial results.",
            "Distinguish access failure from empty success.",
            "Recover locally first; annotate coverage gaps in the final output.",
        ],
        "chapters": ["3. Error Handling in Agent Tools", "8. Agentic Patterns and Task Decomposition"],
    },
    "5.4": {
        "title": "Large codebase exploration",
        "intro": """
<h3>Definition</h3>
<p>In long sessions models start giving inconsistent answers and referring to "typical patterns" instead of the specific classes they already found. Persist findings outside the rolling transcript.</p>
<h3>How it works</h3>
<p>Scratchpad files record key files, data flow, open questions, confirmed assumptions, risks, and next steps. Spawn subagents for "find all tests" or "trace refund-flow dependencies" while the parent coordinates. Summarize one phase before spawning the next. On crash, load a structured manifest and inject slices into prompts. Use <code>/compact</code> when discovery output fills the window.</p>
""",
        "skills": [
            "Delegate verbose exploration to subagents.",
            "Maintain and reread scratchpads.",
            "Inject phase summaries into later agents.",
            "Design crash recovery with manifests, not raw transcript replay.",
        ],
        "chapters": ["10. Claude Code and Claude Agent SDK Workflows", "5. Conversation Context Management"],
    },
    "5.5": {
        "title": "Human review and confidence",
        "intro": """
<h3>Definition</h3>
<p>Aggregate accuracy (97% overall) can hide an 80% field or document type. Self-reported confidence is useful only after calibration on a labeled set. Stratified random sampling of high-confidence outputs detects novel error patterns after you automate.</p>
<p>Do not set an auto-approval threshold until you have segmented accuracy and calibrated scores. After launch, keep sampling — downstream complaints are a lagging, incomplete instrument. Tools should return a derived <code>requires_review</code> plus reasons, not a raw score for the model to interpret.</p>
""",
        "skills": [
            "Segment accuracy before reducing human review.",
            "Calibrate field-level confidence on labeled data.",
            "Route low confidence and contradictory sources to humans.",
            "Stratified-sample high-confidence outputs after automation.",
        ],
        "chapters": ["4. Structured Data Extraction and Validation", "11. Iterative Refinement, Testing, and Evaluation"],
    },
    "5.6": {
        "title": "Provenance and uncertainty",
        "intro": """
<h3>Definition</h3>
<p>Source attribution dies in summarization unless you pass structured claim–source mappings. Conflicting statistics from credible sources should be annotated, not averaged or arbitrarily picked. Temporal data needs publication or collection dates so 2019 and 2025 figures are a trend, not a contradiction.</p>
<p>Each research specialist should emit claim, source id and location, date, method notes, uncertainty language, and whether the finding is established, contested, or insufficient. The synthesizer preserves and merges those records and reports coverage gaps.</p>
<p>Security sits beside reliability: model output is untrusted to your systems; retrieved pages are untrusted to the model. Private data + untrusted content + an outbound channel is an exfiltration path. Remove or gate one leg. Keep secrets out of prompts.</p>
""",
        "skills": [
            "Preserve claim–source maps across agents.",
            "Annotate conflicts with attribution.",
            "Require dates on numerical claims.",
            "Report coverage gaps instead of papering over missing sources.",
        ],
        "chapters": [
            "8. Agentic Patterns and Task Decomposition",
            "4. Structured Data Extraction and Validation",
            "15. Security and Trust Boundaries",
        ],
    },
}

DOMAINS = [
    ("d1", "1", "27%", "Domain 1 — Agentic Architecture & Orchestration", ["1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7"]),
    ("d2", "2", "18%", "Domain 2 — Tool Design & MCP Integration", ["2.1", "2.2", "2.3", "2.4", "2.5"]),
    ("d3", "3", "20%", "Domain 3 — Claude Code Configuration & Workflows", ["3.1", "3.2", "3.3", "3.4", "3.5", "3.6"]),
    ("d4", "4", "20%", "Domain 4 — Prompt Engineering & Structured Output", ["4.1", "4.2", "4.3", "4.4", "4.5", "4.6"]),
    ("d5", "5", "15%", "Domain 5 — Context Management & Reliability", ["5.1", "5.2", "5.3", "5.4", "5.5", "5.6"]),
]

CHAPTER_PAGES = [
    ("ch-1", "Overview of the teaching guide"),
    ("ch-2", "Chapter 1 — API fundamentals"),
    ("ch-3", "Chapter 2 — Tool interfaces"),
    ("ch-4", "Chapter 3 — Error handling"),
    ("ch-5", "Chapter 4 — Extraction and validation"),
    ("ch-6", "Chapter 5 — Context management"),
    ("ch-7", "Chapter 6 — System prompts"),
    ("ch-8", "Chapter 7 — MCP"),
    ("ch-9", "Chapter 8 — Agentic patterns"),
    ("ch-10", "Chapter 9 — Production workflows"),
    ("ch-11", "Chapter 10 — Claude Code and Agent SDK"),
    ("ch-12", "Chapter 11 — Iteration and evaluation"),
    ("ch-13", "Chapter 12 — Model selection"),
    ("ch-14", "Chapter 13 — Prompt caching"),
    ("ch-15", "Chapter 14 — Batch processing"),
    ("ch-16", "Chapter 15 — Security"),
    ("ch-17", "Chapter 16 — Cheat sheet"),
    ("ch-18", "Study strategy"),
    ("ch-19", "Practice scenarios"),
    ("ch-20", "Recommended reading"),
]


def deeper_reading(titles: list[str]) -> str:
    chapter_id = {title: f"ch-{i}" for i, (title, _) in enumerate(CHAPTERS, 1)}
    links = "".join(
        f'<li><a href="#{chapter_id[title]}">{html.escape(title)}</a></li>'
        for title in titles
    )
    return (
        '<div class="card rule"><div class="kicker">Deeper reading (optional)</div>'
        "<p>This task page is the compressed exam lesson: every distinction you need, without the long teaching prose. "
        "If a point still feels fuzzy, open the unabridged chapter. Full chapters were not shortened.</p>"
        f"<ul>{links}</ul></div>"
    )


def overview_html() -> str:
    return """
<div class="kicker">Complete local textbook</div>
<h2>Claude Certified Architect — Foundations</h2>
<p class="meta">Domain tasks are compressed exam lessons. Full chapters are the unabridged teaching text. Official sample questions are not reproduced here — study those privately from your confidential exam guide.</p>
<div class="card rule">
<div class="kicker">How this book is organized</div>
<p><strong>Domains 1–5</strong> are what you study day to day: definitions, mechanisms, tables, required skills, and traps. That is enough to learn the topic. <strong>Full chapters</strong> keep every original paragraph, example, and practice scenario. Open them only when a task still feels thin.</p>
</div>
<h3>The habit the exam rewards</h3>
<p>Ask where responsibility should live. The model interprets language, chooses among well-described options, synthesizes evidence, and adapts plans. Application code owns deterministic guarantees: permissions, compliance thresholds, state persistence, retries, idempotency, validation, and auditability. Tool and schema design shape model behavior. A vague tool looks like a reasoning failure and is actually an interface failure.</p>
<h3>Domain weights</h3>
<table>
<tr><th>Domain</th><th>Weight</th><th>Tasks</th></tr>
<tr><td>1. Agentic Architecture &amp; Orchestration</td><td>27%</td><td>1.1–1.7</td></tr>
<tr><td>2. Tool Design &amp; MCP Integration</td><td>18%</td><td>2.1–2.5</td></tr>
<tr><td>3. Claude Code Configuration &amp; Workflows</td><td>20%</td><td>3.1–3.6</td></tr>
<tr><td>4. Prompt Engineering &amp; Structured Output</td><td>20%</td><td>4.1–4.6</td></tr>
<tr><td>5. Context Management &amp; Reliability</td><td>15%</td><td>5.1–5.6</td></tr>
</table>
<h3>Out of scope on the exam</h3>
<p>You do not need fine-tuning, billing, cloud hosting of MCP, embeddings/vector DB internals, computer use, vision, streaming implementation, rate-limit arithmetic, OAuth details, model internals, or prompt-caching implementation beyond knowing caching exists.</p>
<h3>How to study a task</h3>
<ol>
<li>Read the compressed lesson (definition, mechanism, skills, traps).</li>
<li>Recap the decision rule in one sentence. If you cannot, open the linked Full chapter.</li>
<li>Do the matching lab and at least one practice scenario.</li>
<li>Mark the task studied only when you can explain why the second-best design fails.</li>
</ol>
<p>Study tools in the sidebar: <a href="#method">How to pick the answer</a>, <a href="#principles">Principles</a>, <a href="#pairs">Decision pairs</a>, <a href="#traps">Trap radar</a>, and <a href="#drill">Drill</a>. On a task page use Previous / Next, Recall, and the note box. Keyboard: <code>[</code> previous task, <code>]</code> next, <code>r</code> random unfinished, <code>?</code> this help.</p>
"""


def method_html() -> str:
    return """
<div class="kicker">Study assist</div>
<h2>How to pick the answer</h2>
<p class="meta">Use this on every scenario. The exam usually asks which fix hits the root cause at the earliest safe layer — not which option sounds helpful.</p>
<div class="card rule">
<div class="kicker">90-second procedure</div>
<ol>
<li>Name the failure: boundary, vague rule, inconsistent judgment, bad shape, wrong values, missing gate, noisy context, bad decomposition, missing provenance, or escalation/customer.</li>
<li>Ask which layer is earliest. Do not skip ahead to a fancy pattern that belongs later.</li>
<li>Ask whether the need is <em>judgment</em> (prompt/examples) or a <em>guarantee</em> (code, hook, schema, tool).</li>
<li>Reject options that add tools, agents, window size, or “be careful” unless the failure is specifically “missing the right example.”</li>
</ol>
</div>
<h3>Axioms (derive, don’t memorize)</h3>
<table>
<tr><th>About</th><th>Fact</th><th>So the right answer usually…</th></tr>
<tr><td>Model</td><td>Fallible, stateless, non-deterministic</td><td>Puts checks around it; never “just trust Claude”</td></tr>
<tr><td>Authority</td><td>Some decisions are not the system’s</td><td>Escalates on policy/request, not mood or self-confidence</td></tr>
<tr><td>System</td><td>Reliability comes from shrinking choices</td><td>Scopes tools/agents; rarely adds more</td></tr>
<tr><td>Guarantees</td><td>Prose cannot hold an invariant</td><td>Uses hooks, schemas, tool gates</td></tr>
<tr><td>Information</td><td>Distinct states must stay distinct</td><td>Does not collapse fail vs empty, or valid JSON vs true</td></tr>
<tr><td>Fit</td><td>Mechanism must match the job’s shape</td><td>Batch vs sync, resume vs fork, chain vs explore</td></tr>
</table>
<h3>Earliest-layer tree</h3>
<table>
<tr><th>If the problem is…</th><th>Fix here first</th></tr>
<tr><td>Overlapping tools / too many tools / wrong agent can act</td><td>Rename, split, or scope the interface</td></tr>
<tr><td>Vague instruction (“accurate comments”, “be conservative”)</td><td>Explicit criteria (report vs skip)</td></tr>
<tr><td>Known rule applied inconsistently</td><td>2–4 few-shot examples</td></tr>
<tr><td>Output shape is broken</td><td>Schema / tool_use / structured outputs</td></tr>
<tr><td>Shape is valid, values are wrong</td><td>Semantic checks + retry with the exact errors</td></tr>
<tr><td>A step must always happen, or money/compliance</td><td>Programmatic gate; for money, enforce inside the tool</td></tr>
<tr><td>Context is long, stale, or noisy</td><td>Structured facts, trim tools, scratchpad, or fresh+summary</td></tr>
<tr><td>Duplicated or serial work that is independent</td><td>Partition, then parallel Task calls</td></tr>
<tr><td>Citations or dates disappeared</td><td>Claim–source–date records, not prose summaries</td></tr>
</table>
<h3>Prompt fix or system fix?</h3>
<table>
<tr><th>Symptom</th><th>Kind of fix</th></tr>
<tr><td>Wobbly format or ambiguous judgment</td><td>Prompt: examples or explicit criteria</td></tr>
<tr><td>Must-always order, refund cap, generated-file ban</td><td>System: hook, permission, or tool logic</td></tr>
<tr><td>Wrong tool among many</td><td>System: fewer / clearer tools</td></tr>
<tr><td>Malformed JSON</td><td>System: schema-backed output</td></tr>
<tr><td>Well-formed but false</td><td>System: semantic validation</td></tr>
</table>
<div class="card trap">
<div class="kicker">Tie-break</div>
<p>When two options both sound right, pick the one that acts earlier, preserves more distinct information, and removes the least useful context.</p>
</div>
"""


def pairs_html() -> str:
    return """
<div class="kicker">Study assist</div>
<h2>Decision pairs</h2>
<p class="meta">Most items are “which of these two good techniques fits this shape?” Jump to the task that owns the pair.</p>
<table>
<tr><th>If you are choosing between…</th><th>Open</th></tr>
<tr><td>Continue loop vs return to user</td><td><a href="#1.1">1.1 Agentic loops</a></td></tr>
<tr><td>Full pipeline vs smaller coordinator path</td><td><a href="#1.2">1.2 Coordinator</a></td></tr>
<tr><td>Inherit memory vs pass context / parallel Task calls</td><td><a href="#1.3">1.3 Context passing</a></td></tr>
<tr><td>Prompt instruction vs gate / structured handoff</td><td><a href="#1.4">1.4 Enforcement</a></td></tr>
<tr><td>PostToolUse normalize vs PreToolUse block</td><td><a href="#1.5">1.5 Hooks</a></td></tr>
<tr><td>Prompt chaining vs dynamic decomposition</td><td><a href="#1.6">1.6 Decomposition</a></td></tr>
<tr><td>Resume vs fork vs fresh + summary</td><td><a href="#1.7">1.7 Sessions</a></td></tr>
<tr><td>One mega-tool vs split + lookup-then-act</td><td><a href="#2.1">2.1 Tool interfaces</a></td></tr>
<tr><td>Protocol error vs isError; empty vs failed</td><td><a href="#2.2">2.2 Errors</a></td></tr>
<tr><td>tool_choice auto / any / named</td><td><a href="#2.3">2.3 tool_choice</a></td></tr>
<tr><td>Project vs user MCP; tool vs resource</td><td><a href="#2.4">2.4 MCP</a></td></tr>
<tr><td>Grep vs Glob; Edit vs Read+Write</td><td><a href="#2.5">2.5 Built-in tools</a></td></tr>
<tr><td>User vs project CLAUDE.md; memory vs hook</td><td><a href="#3.1">3.1 CLAUDE.md</a></td></tr>
<tr><td>Skill vs slash command vs always-on notes</td><td><a href="#3.2">3.2 Skills</a></td></tr>
<tr><td>Path rules vs nested CLAUDE.md vs @import</td><td><a href="#3.3">3.3 Path rules</a></td></tr>
<tr><td>Plan mode vs direct execution vs thinking</td><td><a href="#3.4">3.4 Plan mode</a></td></tr>
<tr><td>Sequential fixes vs one message for interacting bugs</td><td><a href="#3.5">3.5 Iteration</a></td></tr>
<tr><td>Same-session review vs independent CI instance</td><td><a href="#3.6">3.6 CI/CD</a></td></tr>
<tr><td>Vague “be careful” vs explicit criteria</td><td><a href="#4.1">4.1 Criteria</a></td></tr>
<tr><td>Long rules vs 2–4 examples</td><td><a href="#4.2">4.2 Few-shot</a></td></tr>
<tr><td>Prompt JSON vs schema; required vs nullable</td><td><a href="#4.3">4.3 Structured output</a></td></tr>
<tr><td>Blind retry vs error-feedback; missing source</td><td><a href="#4.4">4.4 Validation</a></td></tr>
<tr><td>Batch vs real-time; cadence vs 24h window</td><td><a href="#4.5">4.5 Batch</a></td></tr>
<tr><td>Self-review vs cold instance; one pass vs two</td><td><a href="#4.6">4.6 Multi-pass</a></td></tr>
<tr><td>Sliding window vs state object vs reference section</td><td><a href="#5.1">5.1 Context</a></td></tr>
<tr><td>Escalate vs clarify vs solve</td><td><a href="#5.2">5.2 Escalation</a></td></tr>
<tr><td>Swallow error vs abort all vs structured partial</td><td><a href="#5.3">5.3 Propagation</a></td></tr>
<tr><td>Read the tree vs Grep + scratchpad + subagent</td><td><a href="#5.4">5.4 Codebase</a></td></tr>
<tr><td>Aggregate accuracy vs segmented + calibrated review</td><td><a href="#5.5">5.5 Confidence</a></td></tr>
<tr><td>Pick one statistic vs annotate conflict + dates</td><td><a href="#5.6">5.6 Provenance</a></td></tr>
</table>
"""


def traps_html() -> str:
    return """
<div class="kicker">Study assist</div>
<h2>Trap radar</h2>
<p class="meta">If an option matches a family below, it is usually a distractor unless the scenario truly needs that move.</p>
<h3>Add more</h3>
<ul>
<li>More tools, more agents, bigger context window, more “IMPORTANT” prose.</li>
<li>Right family instead: scope, decompose, structure facts, write criteria or examples.</li>
</ul>
<h3>Wish instead of enforce</h3>
<ul>
<li>“Tell the model to always verify identity / never refund over $N.”</li>
<li>Right family: hook, prerequisite gate, or policy inside the tool with no override flag.</li>
</ul>
<h3>Collapse two states</h3>
<ul>
<li>Failed lookup returned as an empty list. Schema-valid treated as true. Angry customer treated as “must escalate.”</li>
<li>Right family: keep fail ≠ empty, shape ≠ meaning, escalate ≠ clarify ≠ solve.</li>
</ul>
<h3>Wrong layer of a good technique</h3>
<ul>
<li>Schema when the values are semantically wrong.</li>
<li>Subagents before the scope is known (explore entry points first).</li>
<li>Few-shot to enforce mandatory order.</li>
<li>@import to reduce tokens (it does not).</li>
</ul>
<h3>Stale or implicit memory</h3>
<ul>
<li>Resume without saying what changed. Assume subagents inherited the parent chat. Trust last week’s tool_result prices.</li>
</ul>
<h3>Diagnostic one-liners</h3>
<ul>
<li>Tool never appears → config/discovery. Tool appears but is ignored → description/selection.</li>
<li>Routing broke right after a system-prompt edit → inspect prompt keywords before rewriting every tool.</li>
<li>Fine-tune / retrain is out of scope for this architecture exam.</li>
</ul>
"""


def drill_html() -> str:
    return """
<div class="kicker">Study assist</div>
<h2>Drill</h2>
<p class="meta">Reveal the answer when you are ready. Mark Missed if you would have gotten it wrong. Next loads a different question.</p>
<div class="btn-row">
  <button type="button" class="btn btn-primary" id="drillNext">Next</button>
  <button type="button" class="btn btn-ghost" id="drillClear">Clear miss list</button>
</div>
<div id="drillCard" class="card drill-card"><p class="meta" style="margin:0">Press Next to start.</p></div>
<p class="meta" id="drillStats"></p>
"""


def labs_html() -> str:
    return """
<div class="kicker">Hands-on</div>
<h2>Labs</h2>
<p class="meta">Reading is not enough for this exam. Build these four labs in your own environment. They are original practice briefs aligned to the official exercise themes, not a copy of confidential worksheets.</p>
<h3>Lab A — Support agent loop</h3>
<p>Build an agent with 3–4 tools whose descriptions are easy to confuse unless written carefully (for example lookup vs update). Implement the loop on <code>stop_reason</code>. Return structured errors with category and retryable flags. Add a hook or tool gate that blocks actions above a money threshold and escalates. Test a message that contains two unrelated issues and require decompose → investigate → synthesize.</p>
<h3>Lab B — Claude Code for a team</h3>
<p>Put standards in project <code>CLAUDE.md</code>. Add path-scoped rules for API files and tests. Add a project skill with <code>context: fork</code> and tight <code>allowed-tools</code>. Configure a shared MCP server in <code>.mcp.json</code> with an env-var token, and a personal server in user/local config. Practice plan mode on a migration and direct execution on a one-line fix.</p>
<h3>Lab C — Extraction pipeline</h3>
<p>Define an extraction tool with required, optional, nullable, and <code>other</code>+detail fields. Prove that absent facts come back <code>null</code>. Implement validation-retry with the document, the bad extract, and the errors. Add few-shot examples for two layouts. Sketch a batch of many documents: join by <code>custom_id</code>, resubmit only failures, compute cadence against a 30-hour SLA. Calibrate review routing by segment, not by a single accuracy number.</p>
<h3>Lab D — Multi-agent research</h3>
<p>Coordinator with <code>Task</code> allowed. At least two specialists. Parallel Task calls in one turn. Structured claim/evidence/source/date outputs. Simulate a specialist timeout and require structured partial error up to the coordinator. Feed two credible conflicting numbers and require both to appear with attribution and a contested-vs-established split.</p>
"""


def principles_html() -> str:
    return """
<div class="kicker">Study assist</div>
<h2>Principles</h2>
<p class="meta">Keep these in mind while you read a scenario. They are the same ideas as the task lessons, written as rules of thumb.</p>

<h3>Where responsibility lives</h3>
<ul>
<li>The <strong>model</strong> interprets language, chooses among well-described options, synthesizes, and adapts.</li>
<li><strong>Application code</strong> owns guarantees: permissions, thresholds, retries, idempotency, validation, audit, state.</li>
<li><strong>Tool and schema design</strong> shape what the model can do. A vague tool looks like a reasoning failure and is usually an interface failure.</li>
<li>A <strong>human</strong> owns policy gaps, high-impact irreversible actions, and uncalibrated automation.</li>
</ul>

<h3>Nature of the model</h3>
<ul>
<li>Claude is <strong>stateless</strong>. It only sees what this request contains. A session id is your lookup key, not model memory.</li>
<li>The system prompt belongs in the top-level <code>system</code> parameter and must be <strong>sent every turn</strong>.</li>
<li>Attention is bounded. A huge window is not the same as every token being used. Structure beats volume.</li>
<li>The model is non-deterministic. It cannot <em>guarantee</em> an invariant. Only a mechanism can.</li>
<li>Fine-tune / retrain is out of scope. Your levers are prompts, tools, context, and orchestration.</li>
</ul>

<h3>Mechanisms over wishes</h3>
<ul>
<li>If it <strong>must always</strong> happen (order, refund cap, never edit generated files), enforce it in a hook, permission, or inside the tool.</li>
<li>Prompts guide judgment. They have a non-zero failure rate.</li>
<li>Do not put an <code>override=true</code> or <code>dry_run</code> flag on a dangerous tool. The model can set it wrong.</li>
<li>Thresholds come from <strong>server-controlled</strong> policy, not from a parameter the model invents.</li>
<li><code>CLAUDE.md</code> and rules are context, not enforcement.</li>
</ul>

<h3>Constrain, don’t add</h3>
<ul>
<li>More tools, more agents, a bigger window, or “be careful” is usually the trap.</li>
<li>Give each agent the <strong>minimum</strong> tools for its role.</li>
<li>Split tools when required fields differ. Compose only mechanical or race-prone steps.</li>
<li>Delegate only when the work would flood the parent, needs a specialist, or can run in parallel.</li>
</ul>

<h3>Match the shape of the work</h3>
<ul>
<li>Known fixed steps → prompt chaining. Next step depends on findings → dynamic decomposition.</li>
<li>Independent slices → partition, then parallel Task calls in one turn. Dependent steps stay serial.</li>
<li>Narrow obvious edit → direct execution. Multi-file / architecture / migration → plan mode.</li>
<li>Plan mode is an approval gate. Extended thinking is reasoning budget. They are not the same.</li>
<li>Continue one path → resume. Compare two paths from one baseline → fork. Stale tool results → fresh session + structured summary.</li>
<li>Interactive / blocking → real-time API. High volume, can wait up to 24h → batch. Join by <code>custom_id</code>.</li>
</ul>

<h3>Agent loops and handoffs</h3>
<ul>
<li>Loop on <code>stop_reason</code>: <code>tool_use</code> → run tools, append results, call again. <code>end_turn</code> → stop. Never trust prose that “sounds done.”</li>
<li>Iteration caps are a safety brake, not the definition of done.</li>
<li>Subagents start empty. Pass every fact they need. Include Task in the parent’s <code>allowedTools</code>.</li>
<li>Pass structured content + metadata (ids, sources, dates), not “synthesize the findings.”</li>
<li>Escalation packets: ids, root cause, amounts, actions taken, recommended next step.</li>
</ul>

<h3>Tools, errors, and MCP</h3>
<ul>
<li>Descriptions decide selection. Overlap causes misrouting. Empty search is success with <code>[]</code>, not an error.</li>
<li><code>auto</code> may skip tools. <code>any</code> forces a tool call. A named tool forces that tool.</li>
<li>Protocol / JSON-RPC error = call never well-formed. <code>isError: true</code> = tool ran, operation failed.</li>
<li>Retry safe read transients <strong>inside the tool</strong>. Do not auto-retry a write timeout (uncertain side effect).</li>
<li>Resources = catalogs you consult. Tools = actions. Annotations like <code>readOnlyHint</code> are untrusted hints.</li>
<li>MCP scope: project <code>.mcp.json</code> is shared. User/local <code>~/.claude.json</code> is personal. Precedence local &gt; project &gt; user, not merged.</li>
<li>Grep = contents. Glob = paths. Edit needs a unique anchor; else Read + Write.</li>
</ul>

<h3>Claude Code configuration</h3>
<ul>
<li>Team standards go in <strong>project</strong> <code>CLAUDE.md</code>, not <code>~/.claude/CLAUDE.md</code>.</li>
<li>Always-on facts → <code>CLAUDE.md</code>. Area conventions → <code>.claude/rules/</code> with <code>paths</code>. Procedure → skill or slash command. Hard ban → hook.</li>
<li><code>@import</code> organizes files; it still costs tokens. Path-scoped rules are what reduce context.</li>
<li>Skill: task nature can load it. Slash command: a human presses the button. <code>context: fork</code> isolates verbose output.</li>
<li>CI: <code>-p</code>, schema-shaped JSON, independent review instance — not the session that wrote the code.</li>
<li>Use <code>/memory</code> before rewriting instructions that “aren’t loading.”</li>
</ul>

<h3>Prompts, schemas, and evaluation</h3>
<ul>
<li>Vague “be conservative” loses to <strong>explicit criteria</strong> (what to report vs skip).</li>
<li>Inconsistent format or judgment → 2–4 few-shot examples, including the ambiguous case.</li>
<li>Schema-backed output beats “respond only with JSON.” Valid JSON is not the same as true data.</li>
<li>Required fields the source may omit pressure hallucination. Use nullable / <code>other</code> + detail / <code>unclear</code>.</li>
<li><code>null</code> = not stated. <code>[]</code> = asked and found none.</li>
<li>Retry with the source + failed output + exact errors. Blind retry is weak. Missing source cannot be retried into existence.</li>
<li>Self-review in the authoring chat is weak. Use a cold instance; large reviews need local then integration passes.</li>
<li>Calibrate confidence on labeled, <strong>segmented</strong> data. Aggregate 97% can hide an 80% field.</li>
</ul>

<h3>Context, escalation, provenance</h3>
<ul>
<li>Exact facts (amounts, allergies, order ids) live in a state object or reference section, not only in a prose summary.</li>
<li>Trim tool results before they pile up. Put key findings first (lost-in-the-middle).</li>
<li>Escalate on policy silence, explicit human request, or inability to progress — not on a turn count, anger, or self-reported confidence.</li>
<li>Frustrated but solvable: acknowledge, offer to finish, keep their choice. Multiple matches: clarify, do not guess.</li>
<li>Fail ≠ empty. Swallowing errors and aborting the whole workflow are both wrong. Annotate coverage gaps.</li>
<li>Conflicting credible numbers stay both, with dates and sources. Do not average or pick silently.</li>
</ul>

<h3>Security and cost (exam-relevant)</h3>
<ul>
<li>Private data + untrusted content + an outbound channel is an exfiltration path. Remove or gate one leg.</li>
<li>Keep secrets out of prompts; inject them in tool code.</li>
<li>Know that prompt caching exists. Do not study cache implementation internals for this exam.</li>
<li>Batch worst case is about 24 hours. Cadence ≈ SLA − 24h − post-process. Resubmit only failed ids.</li>
</ul>

<div class="card rule">
<div class="kicker">Rule of thumb on the exam</div>
<p>Name the failure, fix the <strong>earliest</strong> layer, and prefer the option that <strong>constrains, distinguishes, or enforces</strong> over the one that adds, trusts, or wishes. When two answers both sound right, keep more distinct information and act sooner in the pipeline.</p>
</div>
"""


def build_pages() -> list[dict]:
    pages = [{
        "id": "overview",
        "title": "How to use this textbook",
        "crumb": "Overview",
        "kind": "page",
        "html": overview_html(),
        "search": "overview textbook domains how to study",
    }, {
        "id": "method",
        "title": "How to pick the answer",
        "crumb": "Study tools",
        "kind": "assist",
        "html": method_html(),
        "search": "method axioms decision tree prompt vs structural earliest layer",
    }, {
        "id": "principles",
        "title": "Principles",
        "crumb": "Study tools",
        "kind": "assist",
        "html": principles_html(),
        "search": "principles rules of thumb key points memory enforcement constrain stop_reason",
    }, {
        "id": "pairs",
        "title": "Decision pairs",
        "crumb": "Study tools",
        "kind": "assist",
        "html": pairs_html(),
        "search": "versus pairs resume fork batch plan mode tool_choice",
    }, {
        "id": "traps",
        "title": "Trap radar",
        "crumb": "Study tools",
        "kind": "assist",
        "html": traps_html(),
        "search": "traps distractors add more escalate confidence schema",
    }, {
        "id": "drill",
        "title": "Drill",
        "crumb": "Study tools",
        "kind": "assist",
        "html": drill_html(),
        "search": "drill quiz self-check random practice",
    }]
    for did, num, weight, title, task_ids in DOMAINS:
        tasks = []
        for tid in task_ids:
            meta = TASK_META[tid]
            body = meta["intro"] + skills(meta["skills"]) + checks_html(tid) + deeper_reading(meta["chapters"])
            tasks.append({
                "id": tid,
                "title": meta["title"],
                "html": body,
                "search": f"{tid} {meta['title']} {meta['intro']}",
            })
        pages.append({
            "id": did,
            "domain": num,
            "weight": weight,
            "title": title,
            "kind": "domain",
            "tasks": tasks,
        })

    for pid, label in CHAPTER_PAGES:
        idx = int(pid.split("-")[1]) - 1
        title, body = CHAPTERS[idx]
        pages.append({
            "id": pid,
            "title": label,
            "crumb": "Full chapters",
            "kind": "page",
            "html": f'<div class="kicker">Unabridged chapter</div><h2>{html.escape(title)}</h2>' + md_to_html(body),
            "search": title + " " + body[:2000],
        })
    pages.append({
        "id": "labs",
        "title": "Labs",
        "crumb": "Practice",
        "kind": "page",
        "html": labs_html(),
        "search": "labs hands-on exercises build agent claude code extraction research",
    })
    return pages


CSS = r"""
:root {
  --bg:#0f1419; --bg-elev:#171e27; --bg-hover:#1e2733; --line:#2a3544;
  --text:#e8eef4; --muted:#93a4b8; --accent:#d9773a;
  --accent-soft:rgba(217,119,58,.14); --ok:#3d9b6e; --warn:#c9a227;
  --radius:12px; --sidebar:330px; --shadow:0 16px 40px rgba(0,0,0,.28);
}
[data-theme="light"] {
  --bg:#f4efe6; --bg-elev:#fffdf8; --bg-hover:#efe6d6; --line:#d9cbb4;
  --text:#1f2430; --muted:#5d6b7c; --accent:#b85a22;
  --accent-soft:rgba(184,90,34,.1); --ok:#217a52; --warn:#8a6d12;
  --shadow:0 12px 28px rgba(70,50,20,.08);
}
*{box-sizing:border-box} html,body{margin:0;height:100%}
body{font-family:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;background:var(--bg);color:var(--text);line-height:1.58}
.app{display:flex;min-height:100%}
.sidebar{width:var(--sidebar);flex:0 0 var(--sidebar);background:var(--bg-elev);border-right:1px solid var(--line);height:100vh;position:sticky;top:0;display:flex;flex-direction:column}
.brand{padding:20px 18px 12px;border-bottom:1px solid var(--line)}
.brand h1{font-size:1.05rem;margin:0 0 4px}
.brand p{margin:0;color:var(--muted);font-size:.8rem;font-family:ui-sans-serif,system-ui,sans-serif}
.tools{padding:12px 14px;display:grid;gap:8px;border-bottom:1px solid var(--line);font-family:ui-sans-serif,system-ui,sans-serif}
.tools input,.tools button{width:100%;border:1px solid var(--line);background:var(--bg);color:var(--text);border-radius:8px;padding:8px 10px;font:inherit}
.row{display:flex;gap:8px}.row button{cursor:pointer}.row button:hover{background:var(--bg-hover)}
.progress{color:var(--muted);font-size:.75rem}
.nav{overflow:auto;padding:10px 8px 24px;font-family:ui-sans-serif,system-ui,sans-serif}
.nav-item,.task-link{width:100%;text-align:left;border:0;background:transparent;color:var(--text);cursor:pointer;border-radius:8px;padding:8px 10px;font:inherit}
.nav-item{font-weight:650;display:flex;justify-content:space-between;gap:8px}
.nav-item small{color:var(--muted);font-weight:500}
.nav-item:hover,.task-link:hover,.nav-item.active,.task-link.active{background:var(--accent-soft)}
.task-link.active{color:var(--accent)}
.domain,.group{margin-bottom:6px}
.tasks{display:none;padding:0 0 6px 8px}
.domain.open .tasks,.group.open .tasks{display:block}
.task-link{display:flex;align-items:flex-start;gap:8px;font-size:.82rem;color:var(--muted)}
.task-link .dot{width:8px;height:8px;border-radius:50%;border:1px solid var(--line);margin-top:5px;flex:0 0 8px}
.task-link.done .dot{background:var(--ok);border-color:var(--ok)}
main{flex:1;min-width:0}
.topbar{position:sticky;top:0;z-index:5;display:flex;justify-content:space-between;align-items:center;padding:12px 28px;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(10px);border-bottom:1px solid var(--line);font-family:ui-sans-serif,system-ui,sans-serif}
.crumb{color:var(--muted);font-size:.85rem}
.page{max-width:900px;margin:0 auto;padding:28px 28px 80px}
article.show{display:block;animation:in 220ms ease}
@keyframes in{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
h2{font-size:1.7rem;line-height:1.25;margin:0 0 8px}
h3{font-size:1.12rem;margin:28px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}
h4{font-size:1.02rem;margin:22px 0 8px}
.meta{color:var(--muted);font-family:ui-sans-serif,system-ui,sans-serif;font-size:.86rem;margin-bottom:20px}
p,li{font-size:1.02rem} ul,ol{padding-left:1.2rem} li{margin:6px 0}
table{width:100%;border-collapse:collapse;font-size:.92rem;margin:12px 0 18px;font-family:ui-sans-serif,system-ui,sans-serif}
th,td{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top} th{background:var(--bg-elev)}
pre,code{font-family:ui-monospace,"Cascadia Code",Consolas,monospace;font-size:.86rem}
pre{background:var(--bg-elev);border:1px solid var(--line);border-radius:var(--radius);padding:12px 14px;overflow:auto}
.card{background:var(--bg-elev);border:1px solid var(--line);border-radius:var(--radius);padding:14px 16px;margin:12px 0}
.rule{border-left:3px solid var(--accent)}.trap{border-left:3px solid var(--warn)}.ok{border-left:3px solid var(--ok)}
.kicker{font-family:ui-sans-serif,system-ui,sans-serif;font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);margin:0 0 6px}
.mark{margin-top:28px;font-family:ui-sans-serif,system-ui,sans-serif}
.btn-row,.grade,.assistbar,.pager{display:flex;flex-wrap:wrap;gap:10px;margin:16px 0 8px;font-family:ui-sans-serif,system-ui,sans-serif}
.grade{margin-top:12px}
.btn,#helpBtn{
  font-family:ui-sans-serif,system-ui,sans-serif;font-size:.88rem;font-weight:650;
  border:0;border-radius:999px;padding:10px 16px;cursor:pointer;letter-spacing:.01em
}
.btn:disabled{opacity:.4;cursor:default}
.btn-primary,#doneBtn{background:var(--accent);color:#fff}
.btn-primary:hover,#doneBtn:hover{filter:brightness(1.07)}
.btn-ghost,.assistbar button{
  background:transparent;color:var(--text);border:1px solid var(--line);padding:9px 14px
}
.btn-ghost:hover,.assistbar button:hover{background:var(--bg-hover)}
.btn-reveal{background:var(--accent-soft);color:var(--accent);border:1px solid color-mix(in srgb,var(--accent) 40%,var(--line))}
.btn-reveal:hover{filter:brightness(1.08)}
.btn-ok{background:var(--ok);color:#fff}
.btn-ok:hover{filter:brightness(1.08)}
.btn-warn{background:transparent;color:var(--warn);border:1px solid var(--warn)}
.btn-warn:hover{background:color-mix(in srgb,var(--warn) 14%,transparent)}
#helpBtn{background:var(--bg-elev);border:1px solid var(--line);color:var(--text);padding:6px 12px;margin-right:10px}
#doneBtn{border:0;border-radius:999px;padding:10px 16px;cursor:pointer;font-weight:650}
.menu{display:none} a{color:var(--accent)}
.drill-card{min-height:8.5rem}
.check{background:var(--bg-elev);border:1px solid var(--line);border-radius:var(--radius);padding:12px 14px;margin:10px 0}
.check .answer,.drill-card .answer{margin-top:10px}
.notes{width:100%;min-height:90px;background:var(--bg);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:10px;font:inherit}
.recall article.show h3~*{opacity:.22;filter:blur(3px);pointer-events:none}
.recall article.show h3,.recall .assistbar,.recall .pager,.recall .check,.recall .mark,.recall .kicker,.recall h2{opacity:1;filter:none;pointer-events:auto}
.hidden{display:none!important}
.help{position:fixed;right:16px;bottom:16px;max-width:300px;z-index:8;display:none}
.help.open{display:block}
@media(max-width:900px){
  .sidebar{position:fixed;left:0;top:0;z-index:20;transform:translateX(-105%);transition:transform 180ms ease}
  .sidebar.open{transform:none;box-shadow:var(--shadow)}
  .menu{display:inline-block}
}
"""

JS = r"""
const KEY="cca-study-done-v2";
const NOTE_KEY="cca-notes-v1";
const MISS_KEY="cca-misses-v1";
const pageEl=document.getElementById("page");
const nav=document.getElementById("nav");
const crumb=document.getElementById("crumb");
const search=document.getElementById("search");
function loadDone(){try{return new Set(JSON.parse(localStorage.getItem(KEY)||"[]"));}catch{return new Set();}}
function loadNotes(){try{return JSON.parse(localStorage.getItem(NOTE_KEY)||"{}");}catch{return {};}}
function loadMiss(){try{return JSON.parse(localStorage.getItem(MISS_KEY)||"{}");}catch{return {};}}
let done=loadDone();
let notes=loadNotes();
let misses=loadMiss();
let currentId="overview";
let lastDrillKey="";
function allTasks(){return DATA.filter(d=>d.tasks).flatMap(d=>d.tasks);}
function pagesFlat(){
  const out=[];
  DATA.forEach(p=>{
    if(p.kind==="page"||p.kind==="assist") out.push(p);
    if(p.tasks) p.tasks.forEach(t=>out.push({...t,crumb:p.title,kind:"task"}));
  });
  return out;
}
function btn(html,fn,cls){const b=document.createElement("button");b.type="button";if(cls)b.className=cls;b.innerHTML=html;b.onclick=fn;return b;}
function renderNav(q=""){
  q=q.trim().toLowerCase();
  nav.innerHTML="";
  const add=(el)=>nav.appendChild(el);
  const top=DATA.find(p=>p.id==="overview");
  if(top){const b=btn(top.title,()=>show(top.id),"nav-item"); b.dataset.id=top.id; add(b);}
  const tools=document.createElement("div"); tools.className="group open";
  tools.appendChild(btn("<span>Study tools</span><small>assists</small>",()=>tools.classList.toggle("open"),"nav-item"));
  const tList=document.createElement("div"); tList.className="tasks";
  DATA.filter(p=>p.kind==="assist").forEach(p=>{
    if(q && !(p.title+" "+(p.search||"")).toLowerCase().includes(q)) return;
    const link=btn(p.title,()=>show(p.id),"task-link"); link.dataset.id=p.id; tList.appendChild(link);
  });
  tools.appendChild(tList); add(tools);
  DATA.filter(d=>d.tasks).forEach(domain=>{
    const wrap=document.createElement("div"); wrap.className="domain open";
    wrap.appendChild(btn(`<span>${domain.title.replace("Domain ","D")}</span><small>${domain.weight}</small>`,()=>wrap.classList.toggle("open"),"nav-item"));
    const list=document.createElement("div"); list.className="tasks";
    domain.tasks.forEach(t=>{
      const hay=(t.id+" "+t.title+" "+(t.search||"")).toLowerCase();
      if(q && !hay.includes(q)) return;
      const link=btn(`<span class="dot"></span><span>${t.id} ${t.title}</span>`,()=>show(t.id),"task-link"+(done.has(t.id)?" done":""));
      link.dataset.id=t.id; list.appendChild(link);
    });
    wrap.appendChild(list); if(list.children.length) add(wrap);
  });
  const chWrap=document.createElement("div"); chWrap.className="group";
  chWrap.appendChild(btn("<span>Full chapters</span><small>unabridged</small>",()=>chWrap.classList.toggle("open"),"nav-item"));
  const chList=document.createElement("div"); chList.className="tasks";
  DATA.filter(p=>p.id && p.id.startsWith("ch-")).forEach(p=>{
    if(q && !(p.title+" "+(p.search||"")).toLowerCase().includes(q)) return;
    const link=btn(p.title.replace("Chapter ","Ch " ),()=>show(p.id),"task-link");
    link.dataset.id=p.id; chList.appendChild(link);
  });
  chWrap.appendChild(chList); add(chWrap);
  const labs=DATA.find(p=>p.id==="labs");
  if(labs){const b=btn(labs.title,()=>show("labs"),"nav-item"); b.dataset.id="labs"; add(b);}
}
function find(id){
  for(const p of pagesFlat()) if(p.id===id) return p;
}
function neighbors(id){
  const ids=allTasks().map(t=>t.id);
  const i=ids.indexOf(id);
  return {prev:i>0?ids[i-1]:null, next:i>=0&&i<ids.length-1?ids[i+1]:null};
}
function bindChecks(){
  pageEl.querySelectorAll(".check").forEach(box=>{
    const rev=box.querySelector(".reveal");
    const ans=box.querySelector(".answer");
    const grade=box.querySelector(".grade");
    if(rev) rev.onclick=()=>{ans.classList.remove("hidden"); grade.classList.remove("hidden"); rev.classList.add("hidden");};
    const miss=box.querySelector(".miss");
    if(miss) miss.onclick=()=>{
      misses[box.getAttribute("data-task")+"#"+box.getAttribute("data-n")]=true;
      localStorage.setItem(MISS_KEY,JSON.stringify(misses));
      updateProgress();
      miss.textContent="Saved as missed";
      miss.disabled=true;
    };
  });
}
function wireTaskChrome(item){
  const {prev,next}=neighbors(item.id);
  const bar=document.getElementById("assistbar");
  if(!bar) return;
  document.getElementById("prevBtn").onclick=()=>{if(prev) show(prev);};
  document.getElementById("nextBtn").onclick=()=>{if(next) show(next);};
  if(!prev) document.getElementById("prevBtn").disabled=true;
  if(!next) document.getElementById("nextBtn").disabled=true;
  document.getElementById("recallBtn").onclick=()=>document.body.classList.toggle("recall");
  document.getElementById("randBtn").onclick=()=>show(randomTask());
  const ta=document.getElementById("noteBox");
  if(ta){
    ta.value=notes[item.id]||"";
    ta.oninput=()=>{notes[item.id]=ta.value; localStorage.setItem(NOTE_KEY,JSON.stringify(notes));};
  }
  const db=document.getElementById("doneBtn");
  if(db) db.onclick=()=>{if(done.has(item.id)) done.delete(item.id); else done.add(item.id); localStorage.setItem(KEY,JSON.stringify([...done])); updateProgress(); renderNav(search.value); show(item.id);};
}
function randomTask(){
  const ids=allTasks().map(t=>t.id);
  const missTasks=[...new Set(Object.keys(misses).map(k=>k.split("#")[0]))].filter(id=>ids.includes(id));
  const pool=missTasks.length?missTasks:ids.filter(id=>!done.has(id));
  const use=pool.length?pool:ids;
  return use[Math.floor(Math.random()*use.length)];
}
function allCheckItems(){
  const out=[];
  Object.entries(CHECKS).forEach(([tid,arr])=>arr.forEach((qa,i)=>out.push({tid,n:i+1,q:qa[0],a:qa[1],key:tid+"#"+ (i+1)})));
  return out;
}
function esc(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));}
function pickDrillItem(){
  const items=allCheckItems();
  const missItems=items.filter(x=>misses[x.key]);
  const fresh=items.filter(x=>!misses[x.key] && !done.has(x.tid));
  const other=items.filter(x=>!misses[x.key]);
  let pool;
  if(missItems.length && Math.random()<0.4) pool=missItems;
  else if(fresh.length) pool=fresh;
  else if(other.length) pool=other;
  else pool=items;
  const avoid=pool.filter(x=>x.key!==lastDrillKey);
  const use=avoid.length?avoid:pool;
  return use[Math.floor(Math.random()*use.length)];
}
function drawDrill(){
  const card=document.getElementById("drillCard");
  const stats=document.getElementById("drillStats");
  if(!card) return;
  const items=allCheckItems();
  if(!items.length){card.innerHTML="<p>No questions loaded.</p>"; return;}
  const item=pickDrillItem();
  lastDrillKey=item.key;
  card.innerHTML=`<p class="kicker">Task ${esc(item.tid)}</p><p><strong>${esc(item.q)}</strong></p><button type="button" class="btn btn-reveal reveal">Show answer</button><div class="answer hidden"><p>${esc(item.a)}</p></div><div class="grade hidden"><button type="button" class="btn btn-warn miss">Missed</button></div>`;
  card.querySelector(".reveal").onclick=()=>{
    card.querySelector(".answer").classList.remove("hidden");
    card.querySelector(".grade").classList.remove("hidden");
    card.querySelector(".reveal").classList.add("hidden");
  };
  card.querySelector(".miss").onclick=()=>{
    misses[item.key]=true;
    localStorage.setItem(MISS_KEY,JSON.stringify(misses));
    updateProgress();
    const b=card.querySelector(".miss");
    b.textContent="Saved as missed";
    b.disabled=true;
  };
  const missCount=Object.keys(misses).length;
  stats.textContent=(missCount?missCount+" on the miss list · ":"")+items.length+" questions in the bank";
}
function show(id){
  const item=find(id); if(!item) return;
  currentId=id;
  document.body.classList.remove("recall");
  document.querySelectorAll(".task-link,.nav-item").forEach(el=>el.classList.toggle("active",el.dataset.id===id));
  crumb.textContent=item.crumb||item.title;
  let extra="";
  if(item.kind==="task"){
    extra=`<div class="assistbar" id="assistbar">
      <button type="button" class="btn btn-ghost" id="prevBtn">Previous</button>
      <button type="button" class="btn btn-ghost" id="nextBtn">Next</button>
      <button type="button" class="btn btn-ghost" id="recallBtn">Recall</button>
      <button type="button" class="btn btn-ghost" id="randBtn">Random unfinished</button>
    </div>
    <div class="mark"><button type="button" class="btn btn-primary" id="doneBtn">${done.has(item.id)?"Marked studied — click to undo":"Mark this task studied"}</button></div>
    <h3>Your notes</h3><p class="meta">Saved in this browser only.</p>
    <textarea class="notes" id="noteBox" placeholder="Decision rule in one sentence, plus anything you keep missing..."></textarea>`;
  }
  pageEl.innerHTML=`<article class="show"><div class="kicker">${item.crumb||"Textbook"}</div><h2>${item.kind==="task"?item.id+" — ":""}${item.title}</h2>${item.html||""}${extra}</article>`;
  bindChecks();
  if(item.kind==="task") wireTaskChrome(item);
  if(id==="drill"){
    const n=document.getElementById("drillNext");
    const c=document.getElementById("drillClear");
    if(n) n.onclick=drawDrill;
    if(c) c.onclick=()=>{misses={}; lastDrillKey=""; localStorage.setItem(MISS_KEY,"{}"); updateProgress(); drawDrill();};
  }
  history.replaceState(null,"","#"+id);
  document.getElementById("sidebar").classList.remove("open");
  window.scrollTo(0,0);
}
function updateProgress(){
  const n=allTasks().length;
  const c=[...done].filter(id=>allTasks().some(t=>t.id===id)).length;
  document.getElementById("progress").textContent=c+" / "+n+" tasks marked";
  document.getElementById("progressTop").textContent=c+" / "+n+" · "+Object.keys(misses).length+" misses";
}
search.oninput=()=>renderNav(search.value);
document.getElementById("themeBtn").onclick=()=>{
  const next=document.documentElement.getAttribute("data-theme")==="light"?"":"light";
  document.documentElement.setAttribute("data-theme",next);
  localStorage.setItem("cca-theme",next);
};
document.getElementById("resetBtn").onclick=()=>{if(confirm("Clear studied marks?")){done=new Set(); localStorage.setItem(KEY,"[]"); updateProgress(); renderNav(search.value);}};
document.getElementById("menuBtn").onclick=()=>document.getElementById("sidebar").classList.toggle("open");
document.getElementById("helpBtn").onclick=()=>document.getElementById("help").classList.toggle("open");
if(localStorage.getItem("cca-theme")==="light") document.documentElement.setAttribute("data-theme","light");
document.addEventListener("keydown",e=>{
  if(["INPUT","TEXTAREA"].includes(e.target.tagName)) return;
  if(e.key==="["){const n=neighbors(currentId).prev; if(n) show(n);}
  if(e.key==="]"){const n=neighbors(currentId).next; if(n) show(n);}
  if(e.key==="r"){ if(currentId==="drill") drawDrill(); else show(randomTask()); }
  if(e.key==="?") document.getElementById("help").classList.toggle("open");
});
renderNav(); updateProgress();
window.addEventListener("hashchange",()=>{
  const id=(location.hash||"#overview").slice(1)||"overview";
  if(id!==currentId) show(id);
});
show((location.hash||"#overview").slice(1)||"overview");
"""


def main() -> None:
    pages = build_pages()
    payload = json.dumps(pages, ensure_ascii=False)
    checks_payload = json.dumps(CHECKS, ensure_ascii=False)
    doc = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Claude Architect Foundations — Textbook</title>
<style>__CSS__</style>
</head>
<body>
<div class="app">
<aside class="sidebar" id="sidebar">
  <div class="brand">
    <h1>Architect Foundations</h1>
    <p>Tasks · study tools · full chapters</p>
  </div>
  <div class="tools">
    <input id="search" type="search" placeholder="Search the textbook..."/>
    <div class="row">
      <button id="themeBtn" type="button">Theme</button>
      <button id="resetBtn" type="button">Reset progress</button>
    </div>
    <div class="progress" id="progress">0 / 30 tasks marked</div>
  </div>
  <nav class="nav" id="nav"></nav>
</aside>
<main>
  <div class="topbar">
    <div>
      <button class="menu nav-item" id="menuBtn" type="button">Contents</button>
      <div class="crumb" id="crumb">Overview</div>
    </div>
    <div>
      <button type="button" id="helpBtn">?</button>
      <span class="progress" id="progressTop"></span>
    </div>
  </div>
  <div class="page" id="page"></div>
</main>
</div>
<div class="help card" id="help">
  <div class="kicker">Shortcuts</div>
  <p><code>[</code> previous task · <code>]</code> next task<br/><code>r</code> random unfinished / missed<br/><code>?</code> toggle this help</p>
  <p>Study tools: How to pick the answer, Decision pairs, Trap radar, Drill. Recall blurs the lesson so you can recap first.</p>
</div>
<script>const DATA=__DATA__;const CHECKS=__CHECKS__;__JS__</script>
</body>
</html>
"""
    unknown = []
    for meta in TASK_META.values():
        for title in meta["chapters"]:
            if title not in CHAPTER_HTML:
                unknown.append(title)
    if unknown:
        raise SystemExit("Unknown chapters: " + ", ".join(sorted(set(unknown))))
    doc = (
        doc.replace("__CSS__", CSS)
        .replace("__JS__", JS)
        .replace("__DATA__", payload)
        .replace("__CHECKS__", checks_payload)
    )
    OUT.write_text(doc, encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")
    print("Chapters:", len(CHAPTERS))


if __name__ == "__main__":
    main()
