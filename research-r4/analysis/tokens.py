"""Token attribution per agent and per activity for murmur/solo rollouts.
Each token_count is attributed to the kind of the tool call(s) issued in the model response it closes.
usage: python3 tokens.py WS [WS...]"""
import json, sys, glob, re, collections
COORD = re.compile(r'collaboration__|send_message|wait_agent|followup_task|list_agents|spawn_agent|board|clock')
def kind(name, inp):
    # code-mode cells often mix a board call with a shell command: 'coord' only when no shell command is issued
    if 'exec_command' not in inp and (COORD.search(name) or COORD.search(inp)): return 'coord'
    if re.search(r'git (fetch|pull|merge|rebase|log|diff|show|checkout|switch|reset|cherry)', inp) and 'pytest' not in inp: return 'git-read'
    if re.search(r'pytest|unittest|npm test|cargo test|go test|make test', inp): return 'test'
    if re.search(r'git (fetch|pull|push|merge|rebase|log|diff|show|status|checkout|switch|reset|cherry)', inp): return 'git'
    if re.search(r'apply_patch|cat >|<<', inp) or name == 'apply_patch': return 'edit'
    return 'read/other'
def agent(path):
    by = collections.Counter(); calls = collections.Counter(); pend = []; name = None; ctx = []
    for l in open(path):
        r = json.loads(l); p = r.get('payload') or {}; pt = p.get('type')
        if r['type'] == 'session_meta' and name is None:
            m = re.search(r'"agent_path":"([^"]+)"', l); name = m[1] if m else 'root/solo'
        if pt in ('function_call', 'custom_tool_call'):
            pend.append(kind(p.get('name', ''), str(p.get('input', '')) + str(p.get('arguments', ''))))
        if pt == 'token_count' and p.get('info'):
            n = p['info']['last_token_usage']['input_tokens']; ctx.append(n)
            k = pend[0] if pend else 'message/think'
            by[k] += n; calls[k] += 1; pend = []
    return name, by, calls, ctx
for ws in sys.argv[1:]:
    tot = collections.Counter(); print('==', ws.rstrip('/').split('/')[-1])
    for f in sorted(glob.glob(ws + '/**/sessions/**/rollout-*.jsonl', recursive=True)):
        name, by, calls, ctx = agent(f); tot.update(by)
        if not ctx: continue
        print(f'  {name[-12:]:>12} calls {len(ctx):4d} in {sum(ctx)/1e6:5.1f}M avgctx {sum(ctx)/len(ctx)/1e3:5.0f}K max {max(ctx)/1e3:4.0f}K  ' +
              ' '.join(f'{k}:{v/1e6:.1f}M/{calls[k]}' for k, v in by.most_common()))
    T = sum(tot.values()); print('  TOTAL %.1fM  ' % (T/1e6) + ' '.join(f'{k} {v/T:.0%}' for k, v in tot.most_common()))
