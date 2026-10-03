import ast,pathlib,re,subprocess,tempfile,runpy,os
root=pathlib.Path(__file__).resolve().parents[1] / 'streamlit'
source=(root/'streamlit_app.py').read_text().read_text(encoding='utf-8')
tree=ast.parse(source)
ns={'Path':pathlib.Path,'NORMALIZED_API_URL':'http://backend:8000','PUBLIC_NORMALIZED_API_URL':'http://localhost:8000','CLIENT_ID':'waaxalma-for-elimane'}
for name,file in [('AUDIO_INPUT_MANAGER_FILE','audio_input_manager.js'),('AUDIO_OUTPUT_MANAGER_FILE','audio_output_manager.js'),('CONFERENCE_INPUT_MANAGER_FILE','conference_input_manager.js'),('CONFERENCE_TRANSLATION_CLIENT_FILE','conference_translation_client.html')]:ns[name]=root/file
names={'load_audio_input_manager','load_audio_output_manager','load_conference_input_manager','load_conference_translation_client','load_realtime_client','build_audio_url'}
module=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[])
exec(compile(module,str(root/'streamlit_app.py'),'exec'),ns)
assert ns['build_audio_url']('/static/audio/result.mp3')=='http://localhost:8000/static/audio/result.mp3'
with tempfile.TemporaryDirectory() as out:
 count=0
 for name in ['realtime_client.html','realtime_enhanced_client.html','conference_translation_client.html']:
  html=ns['load_conference_translation_client']() if name.startswith('conference') else ns['load_realtime_client'](root/name)
  assert '__WAAXALMA_API_URL__' not in html and '__WAAXALMA_CLIENT_ID__' not in html
  assert 'http://backend:8000' not in html
  assert 'http://localhost:8000' in html and 'waaxalma-for-elimane' in html
  for i,script in enumerate(re.findall(r'<script\b[^>]*>(.*?)</script>',html,re.S|re.I)):
   if not script.strip():continue
   path=pathlib.Path(out)/f'{name}.{i}.js';path.write_text(script)
   subprocess.run(['node','--check',str(path)],check=True,capture_output=True)
   count+=1
 print(f'UI URL separation, identity injection, generated JavaScript ({count} scripts): OK')
os.environ.update(APP_ENV='production',BACKEND_API_URL='http://backend:8000',PUBLIC_BACKEND_URL='http://localhost:8000',CLIENT_ID='waaxalma-for-elimane')
config=runpy.run_path(str(root/'config.py'))
assert config['API_URL']=='http://backend:8000'
assert config['PUBLIC_API_URL']=='http://localhost:8000'
assert config['CLIENT_ID']=='waaxalma-for-elimane'
print('UI typed environment configuration: OK')
