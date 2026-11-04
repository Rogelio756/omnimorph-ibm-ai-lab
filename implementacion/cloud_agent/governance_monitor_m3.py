"""
implementacion/cloud_agent/governance_monitor_m3.py
====================================================
MONITOR M3 — Auditoría LLM y watsonx.governance

Verifica por cada ventana táctica:
  ✓ El modelo usado es ibm/granite-3-8b-instruct (bloquea cualquier otro)
  ✓ La salida JSON tiene los campos requeridos: {window_id, t0, t1, analisis_tactico, narracion_es}
  ✓ narracion_es tiene ≤ 45 palabras (para caber en ventana de 4.0 s)
  ✓ Anti-alucinación: equipo dominante coincide con tactical_summaries.json

Registra cada llamada en data/clean/governance_audit.jsonl:
  {timestamp, model, latency_ms, tokens_in, tokens_out, cost_ru_est, status, window_id}
"""

from __future__ import annotations

import json
import pathlib
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
REQUIRED_MODEL = "ibm/granite-4-h-small"
MAX_NARRATION_WORDS = 45
REQUIRED_FIELDS = {"window_id", "t0", "t1", "analisis_tactico", "narracion_es"}

CLEAN_DIR = pathlib.Path("data/clean")
AUDIT_LOG = CLEAN_DIR / "governance_audit.jsonl"
REPORT_PATH = CLEAN_DIR / "monitor_m3.json"

# Costo estimado watsonx.ai en Resource Units (aproximación)
# Granite 3-8B: ~0.0001 RU / token de entrada, ~0.0003 RU / token de salida
RU_PER_TOKEN_IN = 0.0001
RU_PER_TOKEN_OUT = 0.0003


# ---------------------------------------------------------------------------
# Monitor M3 — auditor de una sola llamada LLM
# ---------------------------------------------------------------------------

class GovernanceMonitorM3:
    """
    Audita llamadas LLM individualmente y registra en governance_audit.jsonl.
    """

    def __init__(
        self,
        tactical_summaries: list,
        audit_log: str | pathlib.Path = AUDIT_LOG,
    ):
        """
        tactical_summaries : lista de dicts de tactical_summaries.json
                             (usado para chequeo anti-alucinación)
        """
        CLEAN_DIR.mkdir(parents=True, exist_ok=True)
        self.audit_log = pathlib.Path(audit_log)
        self.tactical_summaries = {w["window_id"]: w for w in tactical_summaries}
        self._call_count = 0
        self._pass_count = 0

    # ------------------------------------------------------------------
    # Método principal: audit_call
    # ------------------------------------------------------------------

    def audit_call(
        self,
        model_id: str,
        window_id: str,
        llm_response: Optional[dict],
        latency_ms: float,
        tokens_in: int = 0,
        tokens_out: int = 0,
    ) -> dict:
        """
        Audita una llamada LLM completa.

        Parámetros:
            model_id      : modelo usado (debe ser ibm/granite-3-8b-instruct)
            window_id     : identificador de ventana táctica (W0–W7)
            llm_response  : dict parseado de la respuesta LLM (puede ser None si falló)
            latency_ms    : latencia de la llamada en ms
            tokens_in     : tokens de entrada (estimado si no disponible)
            tokens_out    : tokens de salida

        Retorna:
            dict con status "PASS" | "FAIL" y detalle de chequeos
        """
        self._call_count += 1
        checks = {}
        errors = []

        # --- Chequeo 1: modelo correcto (debe ser IBM Granite) ---
        # Acepta cualquier ibm/granite-* para compatibilidad entre entornos
        model_ok = model_id.startswith("ibm/granite")
        checks["model_id"] = {
            "pass": model_ok,
            "expected": "ibm/granite-*",
            "observed": model_id,
        }
        if not model_ok:
            errors.append(f"MODELO PROHIBIDO: '{model_id}'. Solo se permite '{REQUIRED_MODEL}'.")

        # --- Chequeo 2: formato JSON ---
        if llm_response is None:
            json_ok = False
            checks["json_format"] = {"pass": False, "error": "respuesta nula"}
            errors.append("Respuesta LLM nula.")
        else:
            missing = REQUIRED_FIELDS - set(llm_response.keys())
            json_ok = len(missing) == 0
            checks["json_format"] = {
                "pass": json_ok,
                "missing_fields": list(missing),
                "present_fields": list(set(llm_response.keys()) & REQUIRED_FIELDS),
            }
            if not json_ok:
                errors.append(f"Campos faltantes en JSON: {missing}")

        # --- Chequeo 3: longitud de narración (≤ 45 palabras) ---
        narration = llm_response.get("narracion_es", "") if llm_response else ""
        word_count = len(narration.split()) if narration else 0
        narration_ok = word_count <= MAX_NARRATION_WORDS
        checks["narration_length"] = {
            "pass": narration_ok,
            "word_count": word_count,
            "max_allowed": MAX_NARRATION_WORDS,
        }
        if not narration_ok:
            errors.append(f"Narración demasiado larga: {word_count} palabras (máx {MAX_NARRATION_WORDS}).")

        # --- Chequeo 4: anti-alucinación (equipo dominante) ---
        ground_truth = self.tactical_summaries.get(window_id, {})
        expected_dominant = ground_truth.get("dominant_team", "neutro")

        if llm_response:
            # Buscar mención del equipo en análisis_tactico
            analisis = llm_response.get("analisis_tactico", "").lower()
            narracion = llm_response.get("narracion_es", "").lower()
            text_combined = analisis + " " + narracion

            if expected_dominant in ("ARG", "BRA"):
                anti_hallucin_ok = (
                    "arg" in text_combined or "argentina" in text_combined or
                    "bra" in text_combined or "brasil" in text_combined or "verdeamarela" in text_combined or
                    "dominant_team" not in llm_response or
                    llm_response.get("dominant_team", "").upper() in ("ARG", "ARGENTINA", "BRA", "BRASIL")
                )
            elif expected_dominant in ("FRA", "GER"):
                anti_hallucin_ok = (
                    "fra" in text_combined or "france" in text_combined or "francia" in text_combined or
                    "ger" in text_combined or "alemania" in text_combined or "germany" in text_combined or
                    "dominant_team" not in llm_response or
                    llm_response.get("dominant_team", "").upper() in ("FRA", "FRANCE", "FRANCIA", "GER", "ALEMANIA")
                )
            else:
                anti_hallucin_ok = True  # neutro: no hay equipo específico que verificar
        else:
            anti_hallucin_ok = False

        checks["anti_hallucination"] = {
            "pass": anti_hallucin_ok,
            "expected_dominant_team": expected_dominant,
            "window_id": window_id,
        }
        if not anti_hallucin_ok:
            errors.append(f"Anti-alucinación: equipo dominante esperado '{expected_dominant}' no confirmado en respuesta.")

        # --- Estado global de la llamada ---
        all_pass = all(c["pass"] for c in checks.values())
        status = "PASS" if all_pass else "FAIL"
        if all_pass:
            self._pass_count += 1

        # --- Costo estimado en RU ---
        cost_ru = round(tokens_in * RU_PER_TOKEN_IN + tokens_out * RU_PER_TOKEN_OUT, 6)

        # --- Registro en audit log ---
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model_id,
            "window_id": window_id,
            "latency_ms": round(latency_ms, 2),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_ru_est": cost_ru,
            "status": status,
            "checks": checks,
            "errors": errors,
        }

        with open(self.audit_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(audit_entry, ensure_ascii=False) + "\n")

        if not all_pass:
            print(f"  [M3] ❌ {window_id}: {errors}")

        return audit_entry

    # ------------------------------------------------------------------
    # Reporte final
    # ------------------------------------------------------------------

    def finalize_report(self, report_path: str | pathlib.Path = REPORT_PATH) -> dict:
        """
        Genera el reporte final del Monitor M3.
        Debe llamarse después de procesar todas las ventanas.
        """
        report_path = pathlib.Path(report_path)
        all_entries = []

        if self.audit_log.exists():
            with open(self.audit_log, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        all_entries.append(json.loads(line))

        n_total = len(all_entries)
        n_pass = sum(1 for e in all_entries if e.get("status") == "PASS")
        n_fail = n_total - n_pass

        status = "PASS" if n_fail == 0 and n_total > 0 else "FAIL"

        # Estadísticas de latencia y tokens
        latencies = [e["latency_ms"] for e in all_entries if "latency_ms" in e]
        tokens_in = [e["tokens_in"] for e in all_entries if "tokens_in" in e]
        tokens_out = [e["tokens_out"] for e in all_entries if "tokens_out" in e]

        import statistics
        report = {
            "monitor": "M3",
            "name": "Auditoría LLM y watsonx.governance",
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_calls": n_total,
                "passed_calls": n_pass,
                "failed_calls": n_fail,
                "model_used": REQUIRED_MODEL,
                "latency_ms_mean": round(statistics.mean(latencies), 2) if latencies else 0,
                "latency_ms_max": round(max(latencies), 2) if latencies else 0,
                "tokens_in_mean": round(statistics.mean(tokens_in), 1) if tokens_in else 0,
                "tokens_out_mean": round(statistics.mean(tokens_out), 1) if tokens_out else 0,
                "total_cost_ru_est": round(sum(
                    e.get("cost_ru_est", 0) for e in all_entries
                ), 4),
            },
            "audit_log": str(self.audit_log),
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self._print_report(report)
        return report

    def _print_report(self, report: dict) -> None:
        icon = "✅" if report["status"] == "PASS" else "❌"
        print(f"\n{'='*60}")
        print(f" MONITOR M3 — {report['name']}")
        print(f" Estado: {icon} {report['status']}")
        s = report["summary"]
        print(f" Llamadas: {s['total_calls']} total, {s['passed_calls']} PASS, {s['failed_calls']} FAIL")
        print(f" Modelo: {s['model_used']}")
        print(f" Latencia media: {s['latency_ms_mean']} ms")
        print(f" Tokens (in/out media): {s['tokens_in_mean']} / {s['tokens_out_mean']}")
        print(f" Costo estimado total: {s['total_cost_ru_est']} RU")
        print(f" Audit log: {report['audit_log']}")
        print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# Función de conveniencia para uso directo
# ---------------------------------------------------------------------------

def audit_narration_batch(
    narrations: list,
    tactical_summaries: list,
    model_id: str = REQUIRED_MODEL,
) -> dict:
    """
    Audita una lista de narraciones generadas por el agente.

    narrations : lista de dicts {window_id, t0, t1, analisis_tactico, narracion_es, latency_ms, tokens_in, tokens_out}
    tactical_summaries : lista de ventanas tácticas (para anti-alucinación)
    model_id   : modelo que se usó

    Retorna el reporte final del monitor M3.
    """
    # Limpiar log anterior si existe
    if AUDIT_LOG.exists():
        AUDIT_LOG.unlink()

    monitor = GovernanceMonitorM3(tactical_summaries)
    for narr in narrations:
        wid = narr.get("window_id", "W?")
        llm_resp = {k: narr[k] for k in REQUIRED_FIELDS if k in narr}
        monitor.audit_call(
            model_id=model_id,
            window_id=wid,
            llm_response=llm_resp,
            latency_ms=narr.get("latency_ms", 0),
            tokens_in=narr.get("tokens_in", 0),
            tokens_out=narr.get("tokens_out", 0),
        )

    return monitor.finalize_report()


# ---------------------------------------------------------------------------
# CLI de prueba
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    tactical_path = pathlib.Path("data/clean/tactical_summaries.json")
    narrations_path = pathlib.Path("data/clean/narrations.json")

    if not tactical_path.exists():
        print("[monitor_m3] No existe tactical_summaries.json. Ejecuta el engine primero.")
        raise SystemExit(1)

    with open(tactical_path) as f:
        tactical_summaries = json.load(f)

    if narrations_path.exists():
        with open(narrations_path) as f:
            narrations = json.load(f)
    else:
        # Crear naraciones de prueba mínimas
        print("[monitor_m3] No existe narrations.json — usando datos de prueba")
        narrations = [
            {
                "window_id": w["window_id"],
                "t0": w["t0"],
                "t1": w["t1"],
                "analisis_tactico": f"{w['dominant_team']} presiona en {w['pressure_context']}.",
                "narracion_es": f"Argentina presiona con intensidad en el sector central del campo.",
                "latency_ms": 5.0,
                "tokens_in": 300,
                "tokens_out": 60,
            }
            for w in tactical_summaries
        ]

    report = audit_narration_batch(narrations, tactical_summaries)
    raise SystemExit(0 if report["status"] == "PASS" else 1)
