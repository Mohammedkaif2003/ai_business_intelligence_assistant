import sys
p='app.py'
with open(p,'r',encoding='utf-8') as f:
    s=f.read()
print('TRIPLE_QUOTE_COUNT=', s.count('"""'))
for i,l in enumerate(s.splitlines(), start=1):
    if '"""' in l:
        print('LINE', i, l.strip())
