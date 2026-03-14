import requests
from pathlib import Path

OUT=Path('/home/billy/Desktop/serviceGSM/production')
HDR={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36','Referer':'https://www.gsmarena.com/'}

PHOTOS=[
  ('motorolaPics','moto-g82-5g','https://fdn2.gsmarena.com/vv/bigpic/motorola-moto-g82.jpg'),
  ('motorolaPics','moto-g34-5g','https://fdn2.gsmarena.com/vv/bigpic/motorola-moto-g34-china.jpg'),
  ('motorolaPics','moto-g44-5g','https://fdn2.gsmarena.com/vv/bigpic/motorola-moto-g44-5g.jpg'),
  ('motorolaPics','moto-g54-5g','https://fdn2.gsmarena.com/vv/bigpic/motorola-moto-g54.jpg'),
  ('motorolaPics','moto-g64-5g','https://fdn2.gsmarena.com/vv/bigpic/motorola-moto-g64.jpg'),
  ('motorolaPics','moto-g84-5g','https://fdn2.gsmarena.com/vv/bigpic/motorola-moto-g84.jpg'),
  ('motorolaPics','moto-g85-5g','https://fdn2.gsmarena.com/vv/bigpic/motorola-moto-g85.jpg'),
  ('oneplusPics', 'oneplus-10t','https://fdn2.gsmarena.com/vv/bigpic/oneplus-10t.jpg'),
  ('realmePics',  'realme-gt-2','https://fdn2.gsmarena.com/vv/bigpic/realme-gt2.jpg'),
  ('realmePics',  'realme-gt-2-pro','https://fdn2.gsmarena.com/vv/bigpic/realme-gt2-pro.jpg'),
  ('realmePics',  'realme-gt-neo-3','https://fdn2.gsmarena.com/vv/bigpic/realme-gt-neo3-new.jpg'),
]

ok,failed=0,[]
for folder,slug,url in PHOTOS:
    out=OUT/folder/f'{slug}.jpg'
    if out.exists(): print(f'SKIP {slug}'); continue
    r=requests.get(url,headers=HDR,timeout=15)
    if r.ok and len(r.content)>5000:
        out.write_bytes(r.content); print(f'OK   {slug}'); ok+=1
    else:
        print(f'FAIL ({r.status_code}) {slug}'); failed.append(slug)

print(f'\nDONE OK:{ok} FAILED:{len(failed)}')
for f in failed: print(f'  - {f}')
