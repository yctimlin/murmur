#!/usr/bin/env python3
"""Last reasoning/messages/tool calls of each peer before its task_complete (E4 turn-end forensics). usage: turn_ends.py WS..."""
import json, sys
sys.path.insert(0, "/workspace/r4/tools"); import signatures as S
def txt(p):
    t = p.get("type")
    if t == "reasoning": return "THINK " + " ".join(s.get("text", "") for s in (p.get("summary") or []))
    if t == "message": return "MSG " + " ".join(c.get("text", "") for c in (p.get("content") or []) if isinstance(c, dict))
    if t in ("function_call", "custom_tool_call"): return f"CALL {p.get('name')} " + str(p.get("arguments") or p.get("input") or "")
    return None
for ws in sys.argv[1:]:
    for who, f in sorted(S.rollouts(ws).items()):
        if who == "root": continue
        items = []
        for l in open(f, errors="replace"):
            try: d = json.loads(l)
            except Exception: continue
            p = d.get("payload") or {}
            if d.get("type") == "response_item":
                x = txt(p)
                if x: items.append((d["timestamp"][11:19], x))
            if p.get("type") == "task_complete": items.append((d["timestamp"][11:19], "END " + str(p.get("last_agent_message") or p.get("error"))))
        print(f"\n##### {ws.rsplit('/',1)[-1]} {who} ({len(items)} items)")
        for t, x in items[-9:]: print(t, x[:420].replace("\n", " "))
