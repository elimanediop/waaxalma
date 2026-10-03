// Apply the Streamlit settings to this isolated client before a user starts it.
for (const [id, value] of Object.entries({language: workspaceSettings.target,
    targetLanguage: workspaceSettings.target, sourceLanguage: workspaceSettings.source,
    terminology: workspaceSettings.terminology})) {
    const input = document.getElementById(id);
    if (!input) continue;
    if (input.tagName === 'SELECT' && !Array.from(input.options).some(o => o.value === value)) {
        input.add(new Option(value === 'wo' ? 'Wolof' : value, value));
    }
    input.value = value;
    const field = input.closest('.field, .language-control');
    if (field) field.style.display = 'none';
}
const controls = document.querySelector('.controls');
if (controls) controls.style.gridTemplateColumns = 'auto auto';
