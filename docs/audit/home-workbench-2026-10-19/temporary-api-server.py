from pathlib import Path
import os,tempfile,uvicorn
for key in list(os.environ):
    if key.startswith(('XILIU_','OPENAI_','DEEPSEEK_')): del os.environ[key]
from xiliu.api.app import create_app
with tempfile.TemporaryDirectory(prefix='xiliu-home-workbench-') as temporary:
    data=Path(temporary)
    (data/'.env').write_text('',encoding='utf8')
    app=create_app(data_dir=data,env_file=data/'.env',static_dir=Path('web/dist').resolve())
    uvicorn.run(app,host='127.0.0.1',port=5200,log_level='warning')
