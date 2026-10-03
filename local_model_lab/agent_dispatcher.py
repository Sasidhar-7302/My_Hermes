# -*- coding: utf-8 -*-
"""
Hermes Agent Company - Quota-Aware Agent Dispatcher & Dashboard
"""
import os, io, sys, time, requests
from datetime import datetime
from role_registry import ROLES, PROVIDER_KEY_NAMES, PROVIDER_BASE_URLS
from laya_router import route_request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

_ENV = {}
try:
    with open(os.path.join(os.path.dirname(__file__), '..', '.env'), 'r', encoding='utf-8') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, _, v = line.partition('=')
                _ENV[k.strip()] = v.strip()
except Exception: pass

def get_key(provider):
    key_name = PROVIDER_KEY_NAMES.get(provider)
    if not key_name: return "no-key-needed"
    return _ENV.get(key_name, '')

def call_model(provider, model_id, messages, max_tokens=2048):
    base_url = PROVIDER_BASE_URLS.get(provider)
    api_key  = get_key(provider)
    
    if provider == "gemini":
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}'
        prompt = "\n".join([m["content"] for m in messages])
        payload = {'contents': [{'parts': [{'text': prompt}]}], 'generationConfig': {'maxOutputTokens': max_tokens}}
        start = time.time()
        try:
            r = requests.post(url, json=payload, timeout=45)
            lat = int((time.time()-start)*1000)
            if r.status_code == 200:
                return r.json()['candidates'][0]['content']['parts'][0]['text'], lat, "OK"
            return None, lat, f"HTTP_{r.status_code}"
        except Exception as e:
            return None, 0, str(e)
            
    # Standard OpenAI compat
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model_id, "messages": messages, "max_tokens": max_tokens, "temperature": 0.2}
    start = time.time()
    try:
        r = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=45)
        lat = int((time.time() - start) * 1000)
        if r.status_code == 200:
            content = r.json()['choices'][0]['message'].get('content') or r.json()['choices'][0]['message'].get('reasoning_content') or ''
            return content, lat, "OK"
        return None, lat, f"HTTP_{r.status_code}"
    except Exception as e:
        return None, 0, str(e)

def log_task(role, task, response, latency, model):
    try:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "task": task,
            "response": response,
            "latency_ms": latency,
            "model": model
        }

        # 1. Global task trail
        tasks_file = os.path.join(os.path.dirname(__file__), 'role_tasks.json')
        data = []
        if os.path.exists(tasks_file):
            import json
            try:
                with open(tasks_file, 'r', encoding='utf-8') as f: data = json.load(f)
            except Exception: pass
        data.insert(0, entry)
        with open(tasks_file, 'w', encoding='utf-8') as f:
            import json
            json.dump(data[:100], f, indent=2)

        # 2. Individual Employee Log
        emp_dir = os.path.join(os.path.dirname(__file__), 'employee_logs')
        os.makedirs(emp_dir, exist_ok=True)
        emp_file = os.path.join(emp_dir, f"{role}.json")
        emp_data = []
        if os.path.exists(emp_file):
            import json
            try:
                with open(emp_file, 'r', encoding='utf-8') as f: emp_data = json.load(f)
            except Exception: pass
        emp_data.insert(0, entry)
        with open(emp_file, 'w', encoding='utf-8') as f:
            import json
            json.dump(emp_data[:100], f, indent=2)
    except Exception:
        pass

def dispatch_task(task: str):
    print("\n" + "="*70)
    print("  HERMES MULTI-AGENT DASHBOARD")
    print("="*70)
    
    print(f"  [Task] {task[:60]}...")

    # 0. GLOBAL HARDLINE SAFETY & TELEGRAM CONFIRMATION SHIELD
    try:
        from computer_control import audit_action_safety, SafetyViolationError, ConfirmationRequiredException, request_telegram_confirmation
        audit_action_safety("dispatch_task", task)
    except SafetyViolationError as e:
        print(f"\n  [HARDLINE SECURITY INTERCEPTION] Action Blocked:\n  {str(e)}")
        log_task("SECURITY_SHIELD", task, f"[BLOCKED] {str(e)}", 1, "hardline_guard")
        return
    except ConfirmationRequiredException as e:
        tg_payload = request_telegram_confirmation(e.action_type, e.details)
        print(f"\n  [TELEGRAM CONFIRMATION REQUIRED]\n{tg_payload}")
        log_task("TELEGRAM_GATEWAY", task, f"[AWAITING APPROVAL] {e.details}", 1, "telegram_gate")
        return

    # 1. LAYA ROUTING
    print(f"\n  [System 1] Routing via Laya (ONNX)...")
    route_info = route_request(task)
    target_role = route_info["domain"]
    print(f"  [System 1] Routing Complete in {route_info['latency_ms']}ms")
    print(f"  [Decision] Role: {target_role} | Urgency: {route_info['urgency']}")
    
    if target_role not in ROLES:
        target_role = "CEO"
        
    role_def = ROLES[target_role]
    print(f"\n  [System 2] Dispatching to {target_role} Team")
    print(f"  Fallback Chain (Quota Aware):")
    for i, m in enumerate(role_def["models"]):
        print(f"    {i+1}. {m['name']} ({m['provider']}) - Quota: {m['quota']}")

    if target_role == "OPERATOR":
        try:
            from computer_control import execute_computer_task
            ctrl_res = execute_computer_task(task)
            status = ctrl_res.get("status")
            if status == "blocked":
                print(f"\n  [HARDLINE SECURITY INTERCEPTION] Action Blocked: {ctrl_res.get('reason')}")
                log_task("OPERATOR", task, f"[BLOCKED] {ctrl_res.get('reason')}", 5, "hardline_guard")
                return
            elif status == "awaiting_confirmation":
                print(f"\n  [TELEGRAM CONFIRMATION PENDING]\n{ctrl_res.get('telegram_prompt')}")
                log_task("OPERATOR", task, f"[AWAITING TELEGRAM CONFIRMATION] {ctrl_res.get('action')}", 5, "telegram_gate")
                return
            elif status in ["executed", "completed", "success"]:
                result_content = (
                    ctrl_res.get("message")
                    or (f"Opened in browser: {ctrl_res['url']}" if "url" in ctrl_res else None)
                    or ctrl_res.get("result")
                    or ctrl_res.get("state")
                    or str(ctrl_res)
                )
                print(f"\n  [OPERATOR EXECUTED SAFELY]:")
                if isinstance(result_content, list):
                    for item in result_content[:10]:
                        if isinstance(item, dict):
                            print(f"    - {item.get('title')}")
                        else:
                            print(f"    - {item}")
                else:
                    print(f"    {result_content}")
                log_task("OPERATOR", task, str(result_content), 10, "computer_control")
                return
        except Exception as e:
            print(f"\n  [OPERATOR ERROR]: {e}")

    messages = [{"role": "system", "content": role_def["soul"]}, {"role": "user", "content": task}]
    
    print("\n  Executing...")
    for m in role_def["models"]:
        print(f"  -> Attempting {m['name']}...", end="", flush=True)
        response, lat, err = call_model(m['provider'], m['id'], messages)
        if response:
            log_task(target_role, task, response, lat, m['name'])
            print(f" [SUCCESS] ({lat}ms)")
            print("="*70)
            print("  AGENT OUTPUT:")
            print("="*70)
            print(response)
            print("="*70)
            return
        else:
            print(f" [FAILED] - {err}")
            print(f"  -> Auto-switching to next fallback due to quota/error...")
            
    print("  [CRITICAL] All models failed. Escalating to User.")

if __name__ == "__main__":
    import sys
    task = sys.argv[1] if len(sys.argv) > 1 else "Write a python function to authenticate to a database."
    dispatch_task(task)
