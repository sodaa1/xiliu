from pathlib import Path
from PIL import Image,ImageDraw
p=Path('docs/audit/navigation-assistant-2026-10-19')
def board(a,b,name,labels):
 result=Image.new('RGB',(a.width+b.width,max(a.height,b.height)+38),'#f1eff8');result.paste(a,(0,38));result.paste(b,(a.width,38));d=ImageDraw.Draw(result);d.text((14,10),labels[0],fill='#302947');d.text((a.width+14,10),labels[1],fill='#302947');result.save(p/name)
for page in ['today','workbench','assistant','feed','inbox','knowledge','plans']:
 board(Image.open(p/f'before-{page}.png').convert('RGB'),Image.open(p/f'after-{page}.png').convert('RGB'),f'compare-{page}.png',('BEFORE - EXISTING UI','AFTER - ACTUAL EDGE SCREENSHOT'))
source=Image.open('tmp/ui-reference-20261019/Xiliu_高清页面参考图/助手/01-assistant-main.jpg').convert('RGB');source=source.resize((1440,round(source.height*1440/source.width)),Image.Resampling.LANCZOS)
board(source,Image.open(p/'after-assistant.png').convert('RGB'),'assistant-reference-comparison.png',('USER REFERENCE - NORMALIZED WIDTH 1440','IMPLEMENTATION - ORIGINAL ICON RAIL + EXISTING CAPABILITIES'))
board(Image.open(p/'before-workbench.png').convert('RGB').crop((74,65,1440,225)),Image.open(p/'after-workbench.png').convert('RGB').crop((74,65,1440,225)),'panorama-detail-comparison.png',('PREVIOUS CROPPED REFERENCE ART','NEWLY GENERATED 2039 x 771 ARTWORK'))
print('9 source/before/after comparison boards created')
