import json,re,time,xml.etree.ElementTree as ET
from pathlib import Path
from src.core.adb import ADBDevice
adb=ADBDevice('33005627a45094c1')
def nav(xml):
 out=[]
 try:r=ET.fromstring(xml)
 except:return out
 for n in r.iter('node'):
  a=n.attrib;m=re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]',a.get('bounds',''))
  if a.get('class')!='android.view.View' or a.get('clickable')!='true' or not m:continue
  x1,y1,x2,y2=map(int,m.groups())
  if x2-x1>=150 and y2-y1 in range(100,130) and y1<230:out.append((x1,y1,x2,y2,a.get('selected')=='true'))
 return sorted(out)
def home():
 for _ in range(5):
  x=adb.dump_ui() or '';ns=nav(x)
  if 'Make a post on Facebook' in x and len(ns)==6 and ns[0][4]:return x
  adb.press_back();time.sleep(2)
 raise RuntimeError('no home')
def marks(x):
 low=x.lower(); keys=['notifications','new notifications','marketplace','groups','menu','friends','people you may know','video','reels']
 return [k for k in keys if k in low]
for idx in range(2,6):
 x=home();ns=nav(x);b=ns[idx];adb.tap((b[0]+b[2])//2,(b[1]+b[3])//2);time.sleep(3)
 y=adb.dump_ui() or '';Path(f'tab_remaining_{idx}.xml').write_text(y,encoding='utf-8')
 print(json.dumps({'index':idx,'markers':marks(y),'nav_selected':[i for i,n in enumerate(nav(y)) if n[4]]},ensure_ascii=False))
print('DONE')
