import re, json, sys
raw = open(sys.argv[1], encoding='utf-8').read()
dec = json.JSONDecoder()
# decode Next.js flight chunks: self.__next_f.push([1,"..."])
parts = []
for m in re.finditer(r'self\.__next_f\.push\(\[1,', raw):
    try:
        sstr, _ = dec.raw_decode(raw, m.end())
        parts.append(sstr)
    except Exception:
        pass
s = raw + "\n" + "".join(parts)
out = {}
for m in re.finditer(r'"vegaLiteSpec":', s):
    try:
        obj, _ = dec.raw_decode(s, m.end())
    except Exception:
        continue
    t = obj.get('title', {})
    title = t.get('text') if isinstance(t, dict) else t
    vals = obj.get('data', {}).get('values', [])
    if title and title not in out:
        out[title] = vals
json.dump(out, open(sys.argv[2], 'w'), indent=1)
for k, v in out.items():
    keys = sorted({kk for r in v for kk in r})
    print(f"{k!r}: {len(v)} rows; keys={keys}")
