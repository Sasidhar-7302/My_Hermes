# -*- coding: utf-8 -*-
import requests, time, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

GROQ_KEY   = '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'
GEMINI_KEY = 'AQ.Ab8RN6I3EtU_KABs40ya2iycQeXoq4c23X1JFs1Onsmb5cRj_g'
PROMPT = 'Reply with exactly: ONLINE'

TESTS = [
    # (provider, base_url_or_None, key, model_id, label)
    ('groq', 'https://api.groq.com/openai/v1', GROQ_KEY, 'openai/gpt-oss-120b',  'GPT-OSS 120B'),
    ('groq', 'https://api.groq.com/openai/v1', GROQ_KEY, 'openai/gpt-oss-20b',   'GPT-OSS 20B'),
    ('groq', 'https://api.groq.com/openai/v1', GROQ_KEY, 'qwen/qwen3.8-27b',     'Qwen 3.8 27B'),
    ('gemini', None, GEMINI_KEY, 'gemini-3.8-flash',       'Gemini 3.8 Flash'),
    ('gemini', None, GEMINI_KEY, 'gemini-3.5-flash',       'Gemini 3.5 Flash'),
    ('gemini', None, GEMINI_KEY, 'gemini-3.1-pro-preview', 'Gemini 3.1 Pro Preview'),
    ('gemini', None, GEMINI_KEY, 'gemini-3.1-flash-lite',  'Gemini 3.1 Flash Lite'),
    ('gemini', None, GEMINI_KEY, 'gemini-2.5-flash',       'Gemini 2.5 Flash'),
    ('gemini', None, GEMINI_KEY, 'gemini-2.5-pro',         'Gemini 2.5 Pro'),
    ('gemini', None, GEMINI_KEY, 'gemini-flash-latest',    'Gemini Flash Latest'),
    ('gemini', None, GEMINI_KEY, 'gemini-pro-latest',      'Gemini Pro Latest'),
]

def test_openai(base, key, model_id):
    headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    payload = {'model': model_id, 'messages': [{'role': 'user', 'content': PROMPT}], 'max_tokens': 10}
    start = time.time()
    try:
        r = requests.post(base + '/chat/completions', headers=headers, json=payload, timeout=20)
        lat = int((time.time() - start) * 1000)
        return ('ONLINE' if r.status_code == 200 else 'HTTP_' + str(r.status_code)), lat
    except Exception as e:
        return 'ERR:' + str(e)[:30], 0

def test_gemini(key, model_id):
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={key}'
    payload = {'contents': [{'parts': [{'text': PROMPT}]}], 'generationConfig': {'maxOutputTokens': 10}}
    start = time.time()
    try:
        r = requests.post(url, json=payload, timeout=20)
        lat = int((time.time() - start) * 1000)
        return ('ONLINE' if r.status_code == 200 else 'HTTP_' + str(r.status_code)), lat
    except Exception as e:
        return 'ERR:' + str(e)[:30], 0

print('\n' + '=' * 70)
print('  GROQ + GEMINI MODEL AVAILABILITY TEST')
print('=' * 70)

results = []
for provider, base, key, mid, label in TESTS:
    print(f'  [{provider:<6}] {label:<35}', end='', flush=True)
    if provider == 'groq':
        status, lat = test_openai(base, key, mid)
    else:
        status, lat = test_gemini(key, mid)
    tag = '[OK]  ' if status == 'ONLINE' else '[FAIL]'
    print(f' {tag} {status:<15} {lat}ms')
    results.append({'provider': provider, 'id': mid, 'label': label, 'status': status, 'lat': lat})

online = [r for r in results if r['status'] == 'ONLINE']
print(f'\n  ONLINE: {len(online)}/{len(results)}')
print('=' * 70)
print('  ONLINE (fastest first):')
for r in sorted(online, key=lambda x: x['lat']):
    print(f'  {r["lat"]:>6}ms  [{r["provider"]}] {r["label"]}  ({r["id"]})')
print('=' * 70)
