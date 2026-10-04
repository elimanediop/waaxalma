import json
from pathlib import Path

def configure_live_client(html, *, target_language, source_language, terminology):
    codes = {'Auto': 'auto', 'French': 'fr', 'English': 'en', 'Spanish': 'es', 'Wolof': 'wo'}
    settings = {'target': codes[target_language], 'source': codes[source_language], 'terminology': terminology}
    payload = json.dumps(settings, ensure_ascii=True).replace('<', '\\u003c')
    script = (Path(__file__).resolve().parents[1] / 'assets/js/workspace_settings.js').read_text(encoding='utf-8')
    return html.replace('</body>', '<script>const workspaceSettings = ' + payload + ';\n' + script + '</script></body>', 1)
