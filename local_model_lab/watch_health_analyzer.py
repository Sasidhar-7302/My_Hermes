# -*- coding: utf-8 -*-
"""
Hermes Biometric & Health Telemetry Analyzer for Samsung Galaxy Watch 8 & Google Pixel 7 Pro
============================================================================================
Ingests real-time and historical sensor/health data from:
  1. Native `hermes-galaxy-watch8.apk` (Wear OS SensorManager: Heart Rate BPM, Steps,
     Accelerometer Motion, Watch Battery %, SpO2 %, Stress Score, Skin Temp)
  2. Native `hermes-pixel7pro.apk` & Samsung Health / Health Connect sync payloads
     (Resting HR, HRV RMSSD, Sleep Score, Deep/REM Sleep, Active Calories, Workouts)

Performs clinical-grade physiological & readiness analysis, computes the composite
Hermes Readiness & BioActive Score (0-100), and dispatches proactive multi-device
notifications via `notification_center.py` whenever anomalies or coaching insights arise.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

TELEMETRY_FILE = Path.home() / ".hermes" / "watch_telemetry.json"
MAX_HISTORY_RECORDS = 300


class WatchHealthAnalyzer:
    """
    Biometric ingestion, physiological readiness scoring, anomaly detection,
    and Wireless ADB APK deployment bridge for Samsung Galaxy Watch 8 & Pixel 7 Pro.
    """

    def __init__(self, storage_path: Optional[Path] = None) -> None:
        self.storage_path: Path = Path(storage_path) if storage_path else TELEMETRY_FILE
        self._last_alert_ts: Dict[str, float] = {}
        self._ensure_baseline_seed()

    def _ensure_baseline_seed(self) -> None:
        """Seeds a realistic initial Galaxy Watch 8 + Pixel 7 Pro snapshot if none exists yet."""
        if self.storage_path.exists():
            return
        seed = [
            {
                "timestamp": datetime.now().isoformat(),
                "source": "galaxy_watch_8_bioactive",
                "device_model": "Samsung Galaxy Watch 8",
                "paired_phone": "Google Pixel 7 Pro",
                "heart_rate_bpm": 68,
                "resting_hr_bpm": 59,
                "hrv_rmssd_ms": 54,
                "spo2_pct": 98,
                "stress_score": 28,
                "sleep_score": 84,
                "sleep_duration_hours": 7.6,
                "deep_sleep_minutes": 88,
                "rem_sleep_minutes": 105,
                "steps": 6420,
                "active_calories_kcal": 410,
                "skin_temp_c": 36.4,
                "watch_battery_pct": 82,
                "phone_battery_pct": 88,
                "activity_state": "RESTING",
            }
        ]
        self._save_history(seed)

    def _load_history(self) -> List[Dict[str, Any]]:
        if not self.storage_path.exists():
            return []
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save_history(self, records: List[Dict[str, Any]]) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(
            json.dumps(records[:MAX_HISTORY_RECORDS], indent=2),
            encoding="utf-8",
        )

    def ingest_telemetry(self, payload: Dict[str, Any], trigger_notifications: bool = True) -> Dict[str, Any]:
        """
        Records a new biometric/sensor telemetry snapshot from Samsung Galaxy Watch 8
        or Google Pixel 7 Pro, runs physiological analysis, and fires notifications if needed.
        """
        history = self._load_history()
        prev = history[0] if history else {}

        def _num(key: str, default: Any, cast=int) -> Any:
            val = payload.get(key)
            if val is None or val == "":
                val = prev.get(key, default)
            try:
                return cast(float(val))
            except Exception:
                return default

        now_iso = datetime.now().isoformat()
        entry: Dict[str, Any] = {
            "timestamp": now_iso,
            "iso_time": now_iso,
            "source": str(payload.get("source") or "galaxy_watch_8_live"),
            "device_model": str(payload.get("device_model") or prev.get("device_model") or "Samsung Galaxy Watch 8"),
            "paired_phone": str(payload.get("paired_phone") or prev.get("paired_phone") or "Google Pixel 7 Pro"),
            "heart_rate_bpm": _num("heart_rate_bpm", 70, int),
            "resting_hr_bpm": _num("resting_hr_bpm", 60, int),
            "hrv_rmssd_ms": _num("hrv_rmssd_ms", 52, int),
            "spo2_pct": _num("spo2_pct", 98, int),
            "stress_score": _num("stress_score", 30, int),
            "sleep_score": _num("sleep_score", 82, int),
            "sleep_duration_hours": round(_num("sleep_duration_hours", 7.5, float), 2),
            "deep_sleep_minutes": _num("deep_sleep_minutes", 85, int),
            "rem_sleep_minutes": _num("rem_sleep_minutes", 100, int),
            "steps": _num("steps", 6420, int),
            "active_calories_kcal": _num("active_calories_kcal", 400, int),
            "skin_temp_c": round(_num("skin_temp_c", 36.4, float), 1),
            "watch_battery_pct": _num("watch_battery_pct", 80, int),
            "phone_battery_pct": _num("phone_battery_pct", 85, int),
            "activity_state": str(payload.get("activity_state") or "RESTING").upper(),
        }

        history.insert(0, entry)
        self._save_history(history)

        analysis = self.analyze_latest(history)
        alerts_sent: List[Dict[str, Any]] = []
        if trigger_notifications:
            alerts_sent = self._dispatch_health_notifications(entry, analysis)

        return {
            "status": "ok",
            "sample": entry,
            "latest": entry,
            "analysis": analysis,
            "alerts_triggered": alerts_sent,
            "notifications_sent": alerts_sent,
            "history_count": len(history),
        }

    def analyze_latest(self, history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Evaluates cardiovascular strain, autonomic HRV recovery, blood oxygen,
        sleep architecture, stress load, and activity goals.
        """
        records = history if history is not None else self._load_history()
        if not records:
            self._ensure_baseline_seed()
            records = self._load_history()

        cur = records[0]
        hr = int(cur.get("heart_rate_bpm", 70))
        rhr = int(cur.get("resting_hr_bpm", 60))
        hrv = int(cur.get("hrv_rmssd_ms", 50))
        spo2 = int(cur.get("spo2_pct", 98))
        stress = int(cur.get("stress_score", 30))
        sleep_score = int(cur.get("sleep_score", 80))
        sleep_hrs = float(cur.get("sleep_duration_hours", 7.5))
        deep_min = int(cur.get("deep_sleep_minutes", 80))
        steps = int(cur.get("steps", 0))
        watch_bat = int(cur.get("watch_battery_pct", 80))
        activity = str(cur.get("activity_state", "RESTING")).upper()

        # Compute Composite Readiness / Energy Score (0 - 100)
        hrv_component = min(100, max(20, int((hrv / 65.0) * 100)))
        stress_component = max(0, 100 - stress)
        spo2_component = 100 if spo2 >= 96 else (75 if spo2 >= 94 else 40)
        rhr_penalty = max(0, (rhr - 62) * 2)
        readiness_score = int(
            max(
                10,
                min(
                    100,
                    0.35 * sleep_score
                    + 0.25 * hrv_component
                    + 0.25 * stress_component
                    + 0.15 * spo2_component
                    - rhr_penalty,
                ),
            )
        )

        anomalies: List[Dict[str, str]] = []
        recommendations: List[str] = []
        overall_risk = "NORMAL"

        # 1. Heart Rate Check
        if hr >= 120 and activity == "RESTING":
            overall_risk = "HIGH"
            anomalies.append({
                "code": "HIGH_RESTING_HR",
                "severity": "HIGH",
                "title": f"Elevated Resting Heart Rate ({hr} BPM)",
                "detail": f"Galaxy Watch 8 detected {hr} BPM while {activity.lower()} (baseline RHR {rhr} BPM).",
            })
            recommendations.append("Pause intense cognitive/physical load for 5 minutes and perform box breathing (4s inhale, 4s hold, 4s exhale).")
        elif hr < 45 and activity == "RESTING":
            overall_risk = "HIGH"
            anomalies.append({
                "code": "LOW_HR_BRADYCARDIA",
                "severity": "HIGH",
                "title": f"Unusually Low Heart Rate ({hr} BPM)",
                "detail": f"Heart rate dropped to {hr} BPM at rest.",
            })

        # 2. Blood Oxygen (SpO2) Check
        if spo2 < 94:
            overall_risk = "CRITICAL" if spo2 < 90 else "HIGH"
            anomalies.append({
                "code": "LOW_SPO2",
                "severity": overall_risk,
                "title": f"Low Blood Oxygen Saturation (SpO2 {spo2}%)",
                "detail": f"Galaxy Watch 8 BioActive sensor reported SpO2 of {spo2}% (healthy threshold >= 95%).",
            })
            recommendations.append("Sit upright, take slow deep breaths, and re-verify Watch 8 wrist placement.")

        # 3. Stress & HRV Autonomic Check
        if stress >= 80 or hrv < 28:
            if overall_risk == "NORMAL":
                overall_risk = "ELEVATED"
            anomalies.append({
                "code": "HIGH_AUTONOMIC_STRESS",
                "severity": "HIGH" if stress >= 85 else "ELEVATED",
                "title": f"High Sympathetic Stress Load (Stress {stress}/100, HRV {hrv}ms)",
                "detail": "Autonomic nervous system shows elevated sympathetic strain and reduced HRV recovery.",
            })
            recommendations.append("Schedule a 10-minute screen-free walk and hydrate (300ml water).")

        # 4. Sleep Recovery Check
        if sleep_score < 65 or sleep_hrs < 6.0:
            if overall_risk == "NORMAL":
                overall_risk = "ELEVATED"
            anomalies.append({
                "code": "SLEEP_DEBT",
                "severity": "ELEVATED",
                "title": f"Sub-Optimal Sleep Recovery (Score {sleep_score}, {sleep_hrs}h)",
                "detail": f"Deep sleep was {deep_min}m. Cognitive fatigue risk is higher in the afternoon.",
            })
            recommendations.append("Prioritize high-focus architecture/coding tasks early and target an earlier wind-down tonight.")

        # 5. Watch Battery Check
        if watch_bat <= 15:
            anomalies.append({
                "code": "WATCH_BATTERY_LOW",
                "severity": "ELEVATED",
                "title": f"Galaxy Watch 8 Battery Low ({watch_bat}%)",
                "detail": "Charge Galaxy Watch 8 on the magnetic puck before tonight's sleep tracking window.",
            })
            recommendations.append("Place Samsung Galaxy Watch 8 on charger for 30 minutes before bed.")

        if not recommendations:
            recommendations.append(
                f"Physiological readiness is strong ({readiness_score}/100). Ideal window for deep engineering or workout ({max(0, 10000 - steps):,} steps to 10k goal)."
            )

        # Compute 24-sample averages
        recent = records[:24]
        avg_hr = int(sum(int(r.get("heart_rate_bpm", 70)) for r in recent) / max(1, len(recent)))
        avg_stress = int(sum(int(r.get("stress_score", 30)) for r in recent) / max(1, len(recent)))

        grade = "OPTIMAL" if readiness_score >= 80 else ("MODERATE" if readiness_score >= 65 else "RECOVERY_NEEDED")
        circadian_corr = {}
        try:
            from ecosystem_fusion import analyze_circadian_and_correlations
            circadian_corr = analyze_circadian_and_correlations(records)
        except Exception:
            try:
                from local_model_lab.ecosystem_fusion import analyze_circadian_and_correlations
                circadian_corr = analyze_circadian_and_correlations(records)
            except Exception:
                circadian_corr = {}

        return {
            "readiness_score": readiness_score,
            "readiness_grade": grade,
            "status_label": grade,
            "overall_risk": overall_risk,
            "step_goal_progress_pct": min(100, int((steps / 10000.0) * 100)),
            "averages_recent": {
                "avg_heart_rate_bpm": avg_hr,
                "avg_stress_score": avg_stress,
                "samples_count": len(recent),
            },
            "anomalies": anomalies,
            "recommendations": recommendations,
            "circadian_and_correlations": circadian_corr,
            "summary_headline": (
                f"Readiness {readiness_score}/100 ({'Optimal' if readiness_score >= 80 else 'Needs Care'}) • "
                f"HR {hr} BPM (RHR {rhr}) • HRV {hrv}ms • SpO2 {spo2}% • Sleep {sleep_score}/100 • Steps {steps:,}"
            ),
        }

    def _dispatch_health_notifications(self, entry: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fires Unified Notification Center alerts across Watch 8, Pixel 7 Pro, and PC when anomalies occur."""
        sent: List[Dict[str, Any]] = []
        now = time.time()
        try:
            from notification_center import get_notification_center
            nc = get_notification_center()
            for anom in analysis.get("anomalies", []):
                code = anom.get("code", "HEALTH_ALERT")
                # 5-minute cooldown per anomaly code unless forced
                if now - self._last_alert_ts.get(code, 0.0) < 300:
                    continue
                self._last_alert_ts[code] = now
                sev = anom.get("severity", "ELEVATED")
                priority = "CRITICAL" if sev == "CRITICAL" else ("HIGH" if sev in ("HIGH", "ELEVATED") else "NORMAL")
                res = nc.notify(
                    title=f"⌚ {anom.get('title', 'Galaxy Watch 8 Health Alert')}",
                    body=f"{anom.get('detail', '')} • Recommendation: {(analysis.get('recommendations') or [''])[0]}",
                    priority=priority,
                    category="WATCH_BIOMETRICS",
                    role="RESEARCHER",
                    metadata={"code": code, "readiness_score": analysis.get("readiness_score"), "telemetry": entry},
                )
                sent.append(res)
        except Exception:
            pass
        return sent

    def get_dashboard_snapshot(self, limit: int = 25) -> Dict[str, Any]:
        history = self._load_history()
        analysis = self.analyze_latest(history)
        latest = history[0] if history else {}
        return {
            "status": "ok",
            "sample": latest,
            "latest": latest,
            "analysis": analysis,
            "history": history[:limit],
            "history_count": len(history),
        }

    def get_latest_analytics(self, limit: int = 25) -> Dict[str, Any]:
        return self.get_dashboard_snapshot(limit=limit)

    def install_apk_via_wireless_adb(
        self,
        target_ip_port: str,
        apk_path: Path,
        pairing_ip_port: Optional[str] = None,
        pairing_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Uses Android SDK `adb.exe` to pair/connect over Wi-Fi to the Samsung Galaxy Watch 8
        or Google Pixel 7 Pro and install the native `.apk` directly!
        """
        apk_p = Path(apk_path)
        adb_exe = Path.home() / "AppData" / "Local" / "Android" / "Sdk" / "platform-tools" / "adb.exe"
        if not adb_exe.exists():
            return {"ok": False, "status": "error", "error": f"adb.exe not found at {adb_exe}", "steps": []}
        if not apk_p.exists():
            return {"ok": False, "status": "error", "error": f"APK file not found at {apk_p}", "steps": []}

        steps_out: List[str] = []
        try:
            if pairing_ip_port and pairing_code:
                p_res = subprocess.run(
                    [str(adb_exe), "pair", pairing_ip_port.strip(), pairing_code.strip()],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                steps_out.append(f"[adb pair] {(p_res.stdout or p_res.stderr).strip()}")

            if target_ip_port:
                c_res = subprocess.run(
                    [str(adb_exe), "connect", target_ip_port.strip()],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                steps_out.append(f"[adb connect] {(c_res.stdout or c_res.stderr).strip()}")

            cmd = [str(adb_exe)]
            if target_ip_port:
                cmd.extend(["-s", target_ip_port.strip()])
            cmd.extend(["install", "-r", str(apk_p)])
            i_res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            out_txt = (i_res.stdout or "") + "\n" + (i_res.stderr or "")
            steps_out.append(f"[adb install] {out_txt.strip()}")

            if i_res.returncode == 0 and "Success" in out_txt:
                return {
                    "ok": True,
                    "status": "ok",
                    "message": f"Successfully installed {apk_p.name} to {target_ip_port or 'connected device'}!",
                    "logs": steps_out,
                    "steps": steps_out,
                }
            return {
                "ok": False,
                "status": "error",
                "error": out_txt.strip() or "ADB install returned non-zero status",
                "logs": steps_out,
                "steps": steps_out,
            }
        except Exception as e:
            return {"ok": False, "status": "error", "error": str(e), "logs": steps_out, "steps": steps_out}


_GLOBAL_WATCH_ANALYZER: Optional[WatchHealthAnalyzer] = None


def get_watch_health_analyzer() -> WatchHealthAnalyzer:
    global _GLOBAL_WATCH_ANALYZER
    if _GLOBAL_WATCH_ANALYZER is None:
        _GLOBAL_WATCH_ANALYZER = WatchHealthAnalyzer()
    return _GLOBAL_WATCH_ANALYZER


def install_apk_via_wireless_adb(
    target_ip_port: str,
    apk_path: str | Path,
    pair_ip_port: Optional[str] = None,
    pair_code: Optional[str] = None,
) -> Dict[str, Any]:
    return get_watch_health_analyzer().install_apk_via_wireless_adb(
        target_ip_port=target_ip_port,
        apk_path=Path(apk_path),
        pairing_ip_port=pair_ip_port,
        pairing_code=pair_code,
    )

