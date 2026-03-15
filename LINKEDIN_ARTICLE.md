# Three things nobody tells you about building MCP widgets for Microsoft 365

> **Fair Use Notice**
> This article references publicly available technical specifications, documentation, and product names for informational and educational purposes. No substantial verbatim text has been reproduced from any source. All product names, trademarks, and registered trademarks — including Microsoft 365, Copilot, Adaptive Cards, M365 Agents Toolkit, FastMCP, OpenSky Network, and the Model Context Protocol — are the property of their respective owners. Citations for factual claims are listed at the end. The three technical findings are original observations from first-hand development experience.

---

I spent a weekend building a flight tracker that renders an interactive HTML widget inside Microsoft 365 Copilot.

✅ The tool works. The widget renders. You can click a flight row and get live aircraft state — altitude, speed, heading — without leaving the chat window.

Getting there involved three bugs that are not documented anywhere. That is what this article is about.

---

## 🆕 Something genuinely new happened in January

On **26 January 2026**, Anthropic and OpenAI jointly published a specification extension called **MCP Apps**.

Two competitors. One spec. Co-authored together.

The Model Context Protocol already gave AI assistants a standard way to call tools. MCP Apps extends it so tools can return **interactive HTML widgets** that render directly inside the host — M365 Copilot, ChatGPT, anything that implements the spec.

**What the widget actually is:**
- 🖥️ A live iframe — not a screenshot, not a card
- 🔄 Calls back to your MCP server on user interaction
- 🎨 Responds to theme changes (light / dark)
- 📐 Resizes itself to fit its content
- 🧠 Runs *inside* the AI conversation, not alongside it

> This is the first official extension to MCP since the protocol launched. It is production-ready, not a preview. And almost nobody is talking about it yet.

---

## 🃏 Why this is different from Adaptive Cards

If you have built on M365 or Teams, you have used Adaptive Cards. They work. But they have a fundamental limit.

| | Adaptive Cards | MCP Apps Widget |
|---|---|---|
| **Nature** | Static snapshot | Live application |
| **State** | Lost on every update | Lives in the widget |
| **Interaction** | New card per action | JS call inside iframe |
| **Context window** | Grows with each card payload | Untouched |
| **Data updates** | Replace the card | Update in place |

**The practical difference in one sentence:**
In the flight tracker, clicking a row to fetch live aircraft position is a single JavaScript call. With Adaptive Cards, it would be a new bot message, a new card, a replaced view — and the loss of whatever the user was looking at.

> For anything with more than one level of interaction, MCP Apps is not an improvement to cards. It is a replacement for the entire pattern.

---

## ⚠️ The three things nobody tells you

### Fix 1 — `_meta` goes on the tool *definition*, not the tool *result*

**What the spec says:** put the widget URI in `_meta.ui.resourceUri`.

**What it doesn't say clearly:** *where* that `_meta` lives.

❌ Wrong — in `CallToolResult` (M365 ignores it here entirely)
✅ Right — in the `tools/list` response, on the tool definition

By the time your tool runs, M365 has already decided whether to render a widget. That decision is made at discovery time, not execution time.

**The fix (FastMCP / Python):**
```python
@mcp.tool(
    meta={"ui": {"resourceUri": "ui://widget/flights.html"}}
)
async def get_flights_by_aircraft(...):
    ...
```

**If you use a static `mcp-tools.json` manifest** (required by M365 Agents Toolkit), you must also add `_meta` manually to that file *and* re-provision. Both places. Neither alone is enough.

---

### Fix 2 — `mcp-tools.json` is a snapshot, not a live mirror

M365 Agents Toolkit generates `mcp-tools.json` once by interrogating your running server. That snapshot is then deployed. **It does not update automatically.**

The trap:
1. You fix your server ✅
2. You test the server and confirm `_meta` is there ✅
3. Widget still doesn't render ❓
4. Because the *deployed manifest* still has the old snapshot ❌

> 🔁 **Rule:** Re-provision after every structural change to `mcp-tools.json`.

---

### Fix 3 — `window.openai.toolOutput` isn't always what the spec implies

The widget gets its data via `window.openai.toolOutput`. The spec implies it contains a `structuredContent` field. In M365, it sometimes delivers `structuredContent` *unwrapped* — the data *is* `toolOutput`, not `toolOutput.structuredContent`.

```javascript
var out = window.openai.toolOutput;
var data = (out && out.structuredContent !== undefined)
  ? out.structuredContent : out;   // handle both formats
render(data);
```

Without this: your widget receives the data, renders nothing, and gives you no error message.

**One more gotcha:** `window.openai` is injected by M365 *after* your script runs.
Poll for it — 30 checks × 100ms = 3 seconds is enough.

---

## 🚀 What this actually unlocks

The flight tracker is a demo. Here is what the same pattern does in production:

| Use Case | What the widget does |
|---|---|
| 🎫 **IT service desk** | Live ticket list with per-row escalate button — no portal switch |
| 📋 **Sprint planning** | Reorderable backlog inside the chat; assign and close without leaving |
| 🚨 **Incident response** | Live log viewer where the on-call engineer is already working |
| 💰 **Financial reporting** | Drillable P&L — click a line, see the transactions |
| 🏭 **IoT / operations** | Shop floor sensor widget; acknowledge alerts in chat |
| 🔐 **Security ops** | Alert triage in-line; mark false positives, trigger response |
| 🗺️ **Field operations** | Live map widget with clickable assets and status overlays |
| 📊 **Executive dashboards** | KPI widget that updates as the conversation refines the filter |

**The common thread:** these are all situations where users need to *do something with data*, not just read it.

> Adaptive Cards show data. MCP Apps widgets let you act on it — in place, without losing context.

---

## 💡 The broader point

MCP Apps is **six weeks old** as I write this (March 2026).

- ✅ The spec exists and is production-ready
- ✅ FastMCP supports it (`meta=` parameter, v1.26+)
- ✅ M365 Agents Toolkit supports the full widget lifecycle
- ❌ The *practical* knowledge of what goes wrong isn't written down yet

That is the gap this article fills.

The three fixes above will save you the better part of a day. The use case table above should give you enough to take to a customer or product conversation this week.

**The widget rendered. It was worth it.**

---

*Built with: FastMCP · M365 Agents Toolkit · OpenSky Network API · Microsoft 365 Copilot*
*Full guide and code → repository README*

---

## 📚 Sources and references

| Claim | Source |
|---|---|
| MCP Apps announced 26 January 2026; co-developed by Anthropic and OpenAI | [microsoft/mcp-interactiveUI-samples — README](https://github.com/microsoft/mcp-interactiveUI-samples) |
| MCP Apps specification and `_meta.ui.resourceUri` structure | [microsoft/mcp-interactiveUI-samples — M365 Agents Toolkit Instructions](https://github.com/microsoft/mcp-interactiveUI-samples/blob/main/M365-Agents-Toolkit-Instructions.md) |
| `window.openai` injection model; `toolOutput` / `structuredContent` fields; `callTool` API | [microsoft/mcp-interactiveUI-samples — M365 Agents Toolkit Instructions](https://github.com/microsoft/mcp-interactiveUI-samples/blob/main/M365-Agents-Toolkit-Instructions.md) |
| FastMCP `meta=` parameter introduced in v1.26 | [jlowin/fastmcp](https://github.com/jlowin/fastmcp) |
| Adaptive Cards schema and rendering model | [adaptivecards.io — Documentation](https://adaptivecards.io/documentation/) |
| M365 Agents Toolkit `mcp-tools.json` provisioning lifecycle | [microsoft/mcp-interactiveUI-samples — M365 Agents Toolkit Instructions](https://github.com/microsoft/mcp-interactiveUI-samples/blob/main/M365-Agents-Toolkit-Instructions.md) |
| OpenSky Network flight history and live state APIs | [opensky-network.org — REST API Documentation](https://openskynetwork.github.io/opensky-api/) |

*All URLs accessed March 2026.*
