import json, re, time, xml.etree.ElementTree as ET
from pathlib import Path
from src.core.adb import ADBDevice

SERIAL='33005627a45094c1'
adb=ADBDevice(SERIAL)

def nav_nodes(xml):
    root=ET.fromstring(xml)
    out=[]
    for n in root.iter('node'):
        a=n.attrib
        if a.get('class')!='android.view.View' or a.get('clickable')!='true': continue
        m=re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]',a.get('bounds',''))
        if not m: continue
        x1,y1,x2,y2=map(int,m.groups())
        if 170<=y1<=220 and 270<=y2<=310 and x2-x1>=150:
            out.append((x1,y1,x2,y2,a.get('selected')=='true'))
    return sorted(out)

def classify(xml):
    s=xml.lower()
    markers=[]
    for key in ('news feed','make a post on facebook','people you may know','friends','reel','notifications','new notifications','marketplace','groups','menu'):
        if key in s: markers.append(key)
    return markers

base=adb.dump_ui(); nodes=nav_nodes(base)
print('nodes',nodes)
if len(nodes)!=6 or not nodes[0][4]: raise SystemExit('not verified home navigation')
results=[]
for idx in range(1,6):
    fresh=adb.dump_ui(); current=nav_nodes(fresh)
    if len(current)!=6: raise SystemExit(f'nav unavailable before {idx}')
    b=current[idx]; adb.tap((b[0]+b[2])//2,(b[1]+b[3])//2)
    time.sleep(3)
    after=adb.dump_ui(); Path(f'tab_probe_{idx}.xml').write_text(after,encoding='utf-8')
    adb.shell(f'exec-out screencap -p > /sdcard/ignore',timeout=5) if False else None
    selected=[i for i,n in enumerate(nav_nodes(after)) if n[4]]
    result={'index':idx,'selected':selected,'markers':classify(after),'length':len(after)}
    print(json.dumps(result,ensure_ascii=False)); results.append(result)
    now=nav_nodes(after)
    if len(now)!=6: raise SystemExit(f'nav unavailable after {idx}')
    h=now[0]; adb.tap((h[0]+h[2])//2,(h[1]+h[3])//2); time.sleep(2)
    home=adb.dump_ui()
    hn=nav_nodes(home)
    if len(hn)!=6 or not hn[0][4] or 'make a post on facebook' not in home.lower(): raise SystemExit(f'failed return home after {idx}')
Path('tab_probe_results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print('DONE')
