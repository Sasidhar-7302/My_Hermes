import os, requests, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

GROQ_KEY = os.environ.get('GROQ_API_KEY', '')
if not GROQ_KEY:
    print('GROQ_API_KEY environment variable not set. Please export GROQ_API_KEY.')
    sys.exit(1)
r = requests.get('https://api.groq.com/openai/v1/models',
    headers={'Authorization': f'Bearer {GROQ_KEY}'}, timeout=15)
print('GROQ HTTP:', r.status_code)
if r.status_code == 200:
    models = r.json().get('data', [])
    print(f'Total Groq models: {len(models)}\n')
    for m in sorted(models, key=lambda x: x.get('id','')):
        mid = m.get('id', '')
        ctx = m.get('context_window', m.get('context_length', '?'))
        print(f'  {mid:<55} ctx:{ctx}')
    with open('local_model_lab/groq_models.json', 'w', encoding='utf-8') as f:
        json.dump(r.json(), f, indent=2)
    print('\nSaved to groq_models.json')
else:
    print(r.text[:400])
