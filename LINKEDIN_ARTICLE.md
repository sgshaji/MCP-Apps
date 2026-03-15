# Three things nobody tells you about building MCP widgets for Microsoft 365

> **Fair Use Notice**
> This article references publicly available technical specifications, documentation, and product names for informational and educational purposes. No substantial verbatim text has been reproduced from any source. All product names, trademarks, and registered trademarks — including Microsoft 365, Copilot, Adaptive Cards, M365 Agents Toolkit, FastMCP, OpenSky Network, and the Model Context Protocol — are the property of their respective owners. Citations for factual claims drawn from external sources are listed at the end of this article. The three technical findings described ("the three things nobody tells you") are original observations from first-hand development experience and are not sourced from any third-party publication.

---

I spent a weekend building a flight tracker that renders an interactive HTML widget inside Microsoft 365 Copilot. The tool works. The widget renders. Clicking a flight row fetches live aircraft state without leaving the chat window. It looks, frankly, rather good.

Getting there involved three bugs that are not documented anywhere. That is what this article is about.

But first — why does this matter at all?

---

## Something genuinely new happened in January

On 26 January 2026, Anthropic and OpenAI jointly published a specification extension called MCP Apps. That sentence deserves a moment. Two companies that are, in most respects, competitors, co-authored a protocol extension together. The Model Context Protocol already gave AI assistants a standard way to call tools. MCP Apps extends it to let those tools return interactive HTML widgets that render directly inside the host — M365 Copilot, ChatGPT, anything that implements the spec.

The widget is not a screenshot. It is not a card. It is a live iframe that can call back to your MCP server, respond to theme changes, resize itself, and update in real time. The host injects a `window.openai` object; your widget code reads data from it and can invoke further tool calls through it. The whole thing runs inside the AI conversation, not alongside it.

This is the first official extension to MCP since the protocol launched. It is production-ready, not a preview. And almost nobody is talking about it yet.

---

## Why this is different from Adaptive Cards — and it matters

If you have built anything on Microsoft 365 or Microsoft Teams in the last few years, you have almost certainly used Adaptive Cards. They are the standard way to return structured, visual output from a bot or a connector. They work well. The problem is what they cannot do.

An Adaptive Card is a snapshot. You define a JSON schema, the host renders it, and then it is frozen. If the underlying data changes, the card does not. If the user wants to drill into a row, you send a new card. Every interaction requires a round-trip through the bot framework, and each response replaces what came before. Context — what the user was looking at, which row they had expanded, what state they had built up — is lost on every update.

An MCP Apps widget is a running application. The state lives in the widget. Expanding a row, fetching live data, rendering a chart, switching between views — all of that happens inside the iframe without touching the conversation thread. The AI model's context window is not consumed by repeated card payloads. The user does not lose their place.

The practical difference: in a flight tracker, clicking a row to fetch live aircraft position is a single JavaScript function call from inside the widget to the MCP server. With Adaptive Cards, it would be a new bot message, a new card, a replaced view, and the loss of whatever the user was looking at before.

For anything with more than one level of interaction, MCP Apps is a fundamentally different paradigm. Not an improvement to cards — a replacement for the entire pattern.

---

## The three things nobody tells you

### 1. `_meta` must be on the tool definition, not the tool result

The MCP Apps specification says the widget URI goes in `_meta.ui.resourceUri`. What it does not spell out clearly enough is *where* that `_meta` lives.

My first instinct was to put it in `CallToolResult` — that is what the tool returns, so naturally that is where the widget reference should go. M365 Copilot ignores it there entirely. The host reads `_meta` from the `tools/list` response, at the point where it discovers what tools are available. By the time your tool runs, the decision about whether to render a widget has already been made.

In FastMCP (Python), the fix is one parameter on the decorator: `meta={"ui": {"resourceUri": "ui://widget/flights.html"}}`. If you are using a static `mcp-tools.json` manifest — which M365 Agents Toolkit requires — you also need to add `_meta` manually to that file and re-provision your agent. Both places. Neither alone is sufficient.

### 2. `mcp-tools.json` is a snapshot, not a live reflection

M365 Agents Toolkit generates `mcp-tools.json` by interrogating your running MCP server. That file is then bundled into your agent manifest and deployed. From that point on, it does not update automatically.

This means: if you fix your server to add `_meta` to the tool definition, and you test your server and confirm it is returning `_meta` correctly, your deployed agent still has the old snapshot with no `_meta`. The widget will not render. The server is correct. The manifest is stale.

Re-provision after every structural change to `mcp-tools.json`. This is easy to forget when you are focused on server-side fixes.

### 3. `window.openai.toolOutput` is not always what the spec implies

The widget receives its initial data through `window.openai.toolOutput`. The spec suggests `toolOutput` contains a `structuredContent` field. In M365, it sometimes delivers `structuredContent` unwrapped — the data is `toolOutput` itself, not `toolOutput.structuredContent`.

Handle both:

```javascript
var out = window.openai.toolOutput;
var data = (out && out.structuredContent !== undefined)
  ? out.structuredContent : out;
render(data);
```

One line of defensive code. Without it, your widget receives the data but renders nothing, and there is no error message to tell you why.

Also: `window.openai` is injected by M365 *after* your script runs. Poll for it — a loop of thirty checks at 100ms intervals is enough.

---

## What this actually unlocks

The flight tracker is a demonstration. Here is what the same pattern enables in production systems:

**IT service desks.** A support ticket tool returns a widget showing all open tickets, their status, and an "escalate" button per row. The agent handles the language; the widget handles the interaction. No portal switch required.

**Sprint planning.** Query your project management system; render a drag-reorderable backlog inside the chat. Reprioritise, assign, and close items without leaving the conversation where the team just discussed them.

**Incident response.** A live log viewer widget inside the chat where the on-call engineer is already working through the incident. Filter, expand, copy — all without context switching.

**Financial reporting.** An interactive P&L table where clicking a line item drills into the underlying transactions. The model explains the trend; the widget lets the analyst explore the data.

**IoT and operational dashboards.** A shop floor or warehouse widget that polls live sensor data, highlights anomalies, and lets an operator acknowledge alerts — all from a chat interface that also has the maintenance history and the vendor contacts.

**Security operations.** Alert triage in a widget. The model provides the initial analysis; the analyst clicks through indicators, marks false positives, and triggers response actions without leaving the conversation thread.

The common thread: these are all situations where the user needs to *do something with data*, not just *read it*. Adaptive Cards can display data. MCP Apps widgets let users act on it, in place, without losing context.

---

## The broader point

MCP Apps is six weeks old as I write this. The tooling is maturing rapidly — FastMCP added the `meta=` parameter in version 1.26, and the M365 Agents Toolkit supports the full widget lifecycle. The gaps right now are in documentation: the spec exists, the implementations work, but the *practical* knowledge of what goes wrong and why is not written down yet.

That is the gap I ran into. That is what this article is.

If you are building on MCP, it is worth understanding this extension now, before everyone else does. The three fixes above will save you the better part of a day. The use cases above should give you enough to take to a customer or a product conversation next week.

The widget rendered. It was worth it.

---

*Built with: FastMCP · M365 Agents Toolkit · OpenSky Network API · Microsoft 365 Copilot*
*Source: [flight-tracker-mcp](https://github.com) — full guide and code in the repository README.*

---

## Sources and references

| Claim | Source |
|---|---|
| MCP Apps announced 26 January 2026; co-developed by Anthropic and OpenAI | [microsoft/mcp-interactiveUI-samples — README](https://github.com/microsoft/mcp-interactiveUI-samples) |
| MCP Apps specification and `_meta.ui.resourceUri` structure | [microsoft/mcp-interactiveUI-samples — M365 Agents Toolkit Instructions](https://github.com/microsoft/mcp-interactiveUI-samples/blob/main/M365-Agents-Toolkit-Instructions.md) |
| `window.openai` injection model; `toolOutput` and `structuredContent` fields; `notifyIntrinsicHeight`; `callTool` API | [microsoft/mcp-interactiveUI-samples — M365 Agents Toolkit Instructions](https://github.com/microsoft/mcp-interactiveUI-samples/blob/main/M365-Agents-Toolkit-Instructions.md) |
| FastMCP `meta=` parameter introduced in version 1.26 | [jlowin/fastmcp — PyPI / changelog](https://github.com/jlowin/fastmcp) |
| Adaptive Cards schema and rendering model (snapshot / JSON-defined card) | [adaptivecards.io — Documentation](https://adaptivecards.io/documentation/) |
| M365 Agents Toolkit `mcp-tools.json` generation and provisioning lifecycle | [microsoft/mcp-interactiveUI-samples — M365 Agents Toolkit Instructions](https://github.com/microsoft/mcp-interactiveUI-samples/blob/main/M365-Agents-Toolkit-Instructions.md) |
| OpenSky Network flight history and live state APIs | [opensky-network.org — REST API Documentation](https://openskynetwork.github.io/opensky-api/) |

*All URLs accessed March 2026. URLs are provided for attribution; the author does not control their availability or future content.*
