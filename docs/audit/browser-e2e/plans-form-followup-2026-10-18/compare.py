from PIL import Image, ImageDraw
from pathlib import Path
out=Path(__file__).resolve().parent
ref=Image.open(out/'source-modal-crop.png').convert('RGB')
render=Image.open(out/'form-empty-content.png').convert('RGB')
ref=ref.resize((980, round(ref.height*980/ref.width)))
canvas=Image.new('RGB',(2008,max(ref.height,render.height)+74),'#eeeeF5')
canvas.paste(ref,(16,58));canvas.paste(render,(1012,58))
draw=ImageDraw.Draw(canvas);draw.text((16,20),'USER REFERENCE - crop, proportional scale',fill='#383356');draw.text((1012,20),'ACTUAL IMPLEMENTATION - 1536 x 1024 viewport',fill='#383356')
canvas.save(out/'reference-comparison.png')
left=Image.new('RGB',(1260,650),'#eeeeF5')
left.paste(ref.crop((18,125,610,760)),(12,10))
left.paste(render.crop((18,125,610,760)),(650,10))
left.save(out/'reference-comparison-form-detail.png')
