"""
scripts/probar_cronica.py
=========================
Pruebas automáticas de C3a / C3a.1 (Narrador, M3, exportador en carpeta temporal):
a. Tres textos falsos (palabra prohibida, territorio contrario, número inventado) dan FAIL; uno correcto da PASS.
b. Número real pero del equipo equivocado: FAIL. "presencia": PASS. 19 palabras: FAIL. Números en letras -> FAIL ("escribe las cifras con dígitos").
c. Las 8 frases viejas de data/clean/narrations.json, contra las reglas nuevas: cuántas fallan y por qué.
d. La plantilla offline de las 8 ventanas reales pasa M3 (con costo 0 RU).
e. Modelo falso que falla 1 vez y luego acierta: 2 intentos registrados, estado final PASS. Uno que falla siempre: queda offline (con WARNING y online_calls/offline_calls separados).
f. Modelo no Granite: FAIL.
g. El exportador en carpeta temporal no contiene NaN ni claves viejas, conserva árbitros con team=2, interpola el balón, y el rastro 29 sale con equipo SKN en el cuadro 600 y CRC en el 800.
h. Las 5 frases prohibidas/engañosas de C3a.1 dan FAIL, las 2 válidas dan PASS y la de "encierra" da FAIL por "encierra".
i. Huecos de M3 cerrados (26/11): los errores de Granite del 25/11 (W0 «repartido» con territorio de CRC;
   W1/W3 Costa Rica «en la mitad rival» con 40 y 34 %) dan FAIL, igual que no nombrar al equipo con territorio,
   «su mitad» con 88 %, «sube sus líneas» y «retrasa»; «88 por ciento», «no llega a la mitad rival» y W2 correcto dan PASS.

(c) Desde el 26/11 la prueba c revisa que las 8 frases publicadas en data/clean/narrations.json pasen M3.

Todo corre en carpeta temporal sin tocar data/clean, dashboard/data ni dashboard/media.
Sale con código 0 si todas pasan, o 1 si alguna falla.
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from implementacion.cloud_agent import agent_narrator as narr
from implementacion.cloud_agent.governance_monitor_m3 import (
    GovernanceMonitorM3,
    REQUIRED_MODEL,
)
import scripts.export_dashboard_data as exp_dash

CLEAN_DIR = ROOT / "data" / "clean"


class _FakeModelFailOnceThenPass:
    """Modelo simulado que falla en el primer intento (usa palabra prohibida) y acierta en el segundo."""

    def __init__(self, good_resp_by_w: dict[str, dict]):
        self.calls_by_w: dict[str, int] = {}
        self.good_resp_by_w = good_resp_by_w
        self.last_prompt_by_w: dict[str, str] = {}

    def chat(self, messages: list[dict]) -> dict:
        prompt = messages[-1]["content"]
        # Identificar window_id en el prompt
        wid = "W0"
        for w in self.good_resp_by_w:
            if f'"{w}"' in prompt or f"tramo {w}" in prompt:
                wid = w
                break
        self.calls_by_w[wid] = self.calls_by_w.get(wid, 0) + 1
        self.last_prompt_by_w[wid] = prompt

        if self.calls_by_w[wid] == 1:
            bad = dict(self.good_resp_by_w[wid])
            bad["narracion_es"] = "San Cristóbal y Nieves presiona y domina la posesión en el campo."
            txt = json.dumps(bad, ensure_ascii=False)
        else:
            txt = json.dumps(self.good_resp_by_w[wid], ensure_ascii=False)

        return {
            "choices": [{"message": {"content": txt}}],
            "usage": {"prompt_tokens": 120, "completion_tokens": 45},
        }


class _FakeModelAlwaysFail:
    """Modelo simulado que siempre falla las reglas de M3."""

    def chat(self, messages: list[dict]) -> dict:
        bad = {
            "window_id": "W0",
            "t0": 0.0,
            "t1": 4.5,
            "analisis_tactico": "Costa Rica domina la posesión con 999 metros de bloque.",
            "narracion_es": "Costa Rica presiona y controla el partido con dominio absoluto.",
        }
        return {
            "choices": [{"message": {"content": json.dumps(bad, ensure_ascii=False)}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 40},
        }


def main() -> int:
    resultados: list[tuple[str, bool, str]] = []

    def registrar(nombre: str, ok: bool, detalle: str) -> None:
        resultados.append((nombre, ok, detalle))
        marca = "PASS" if ok else "FAIL"
        print(f"  [{marca}] {nombre} -> {detalle}")

    print("=" * 80)
    print("  PRUEBAS C3a · CRÓNICA, MONITOR M3 Y EXPORTADOR (scripts/probar_cronica.py)")
    print("=" * 80)

    with open(CLEAN_DIR / "tactical_summaries.json", "r", encoding="utf-8") as f:
        tactical_real = json.load(f)

    w0 = tactical_real[0]  # W0: territorio="CRC", SKN={pos:36.9, pct:6, largo:17.9, ancho:38.4}, CRC={pos:70.5, pct:88, largo:12.1, ancho:37.5}

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = pathlib.Path(tmpdir)

        # ── a. Tres textos falsos dan FAIL y uno correcto da PASS ────────────
        mon_a = GovernanceMonitorM3([w0], audit_log=tmp / "audit_a.jsonl")

        # 1) Palabra prohibida
        r_prohibida = {
            "window_id": "W0", "t0": 0.0, "t1": 4.5,
            "analisis_tactico": "San Cristóbal y Nieves se ubica a 37 m de su portería con 6% en campo rival. Costa Rica se ubica a 70 m con 88% en campo rival.",
            "narracion_es": "Costa Rica presiona en campo rival mientras San Cristóbal se repliega.",
        }
        res_a1 = mon_a.audit_call(REQUIRED_MODEL, "W0", r_prohibida, 10.0, 100, 40, mode="online")

        # 2) Territorio contrario (W0 es de CRC, pero afirma que SKN está adelantado en campo rival)
        r_terr_mal = {
            "window_id": "W0", "t0": 0.0, "t1": 4.5,
            "analisis_tactico": "San Cristóbal y Nieves juega adelantado en campo rival a 37 m. Costa Rica se ubica a 70 m con 88% en campo rival.",
            "narracion_es": "San Cristóbal y Nieves juega adelantado en campo contrario.",
        }
        res_a2 = mon_a.audit_call(REQUIRED_MODEL, "W0", r_terr_mal, 10.0, 100, 40, mode="online")

        # 3) Número inventado (55 m no está en W0)
        r_num_inv = {
            "window_id": "W0", "t0": 0.0, "t1": 4.5,
            "analisis_tactico": "San Cristóbal y Nieves se ubica a 55 m de su portería. Costa Rica se ubica a 70 m con 88% en campo rival.",
            "narracion_es": "Costa Rica juega adelantado en campo rival.",
        }
        res_a3 = mon_a.audit_call(REQUIRED_MODEL, "W0", r_num_inv, 10.0, 100, 40, mode="online")

        # 4) Texto correcto
        r_ok = {
            "window_id": "W0", "t0": 0.0, "t1": 4.5,
            "analisis_tactico": "San Cristóbal y Nieves se ubica a 37 m de su portería con 6% en campo rival, ocupando 18 m de largo por 38 m de ancho. Costa Rica se ubica a 70 m de su portería con 88% en campo rival, ocupando 12 m de largo por 38 m de ancho.",
            "narracion_es": "Costa Rica juega adelantado, a 70 metros de su portería; San Cristóbal y Nieves queda en su mitad.",
        }
        res_a4 = mon_a.audit_call(REQUIRED_MODEL, "W0", r_ok, 10.0, 100, 40, mode="online")

        ok_a = (
            res_a1["status"] == "FAIL" and not res_a1["checks"]["forbidden_words"]["pass"]
            and res_a2["status"] == "FAIL" and not res_a2["checks"]["territory_consistency"]["pass"]
            and res_a3["status"] == "FAIL" and not res_a3["checks"]["numbers_accuracy"]["pass"]
            and res_a4["status"] == "PASS"
        )
        registrar(
            "a. 3 textos falsos (prohibida, territorio contrario, número inventado) -> FAIL; 1 correcto -> PASS",
            ok_a,
            f"prohibida={res_a1['status']}, territorio={res_a2['status']}, num_inventado={res_a3['status']}, correcto={res_a4['status']}",
        )

        # ── b. Número real pero del equipo equivocado: FAIL; "presencia": PASS; 19 palabras: FAIL; cifras en letras: FAIL
        mon_b = GovernanceMonitorM3([w0], audit_log=tmp / "audit_b.jsonl")

        # 88 es de CRC, pero aquí se le atribuye a San Cristóbal y Nieves
        r_num_cruzado = {
            "window_id": "W0", "t0": 0.0, "t1": 4.5,
            "analisis_tactico": "San Cristóbal y Nieves tiene 88% de ubicación a 37 m de su portería. Costa Rica se ubica a 70 m con 12 m de largo.",
            "narracion_es": "Costa Rica juega adelantado en campo rival.",
        }
        res_b1 = mon_b.audit_call(REQUIRED_MODEL, "W0", r_num_cruzado, 10.0, 100, 40, mode="online")

        # "presencia" y "presidente" NO son palabras prohibidas
        r_presencia = {
            "window_id": "W0", "t0": 0.0, "t1": 4.5,
            "analisis_tactico": "San Cristóbal y Nieves registra presencia a 37 m de su portería con 6% en campo rival. Costa Rica mantiene presencia a 70 m con 88% en campo rival.",
            "narracion_es": "Costa Rica muestra presencia adelantada en campo rival; San Cristóbal y Nieves queda en su mitad.",
        }
        res_b2 = mon_b.audit_call(REQUIRED_MODEL, "W0", r_presencia, 10.0, 100, 40, mode="online")

        # 19 palabras en narracion_es -> FAIL
        r_19_palabras = {
            "window_id": "W0", "t0": 0.0, "t1": 4.5,
            "analisis_tactico": r_ok["analisis_tactico"],
            "narracion_es": "Costa Rica juega muy adelantado en la mitad rival mientras San Cristóbal y Nieves queda ubicado cerca del área.",  # 19 palabras
        }
        res_b3 = mon_b.audit_call(REQUIRED_MODEL, "W0", r_19_palabras, 10.0, 100, 40, mode="online")

        # Número en letras ("setenta") -> FAIL con "escribe las cifras con dígitos"
        r_num_letras = {
            "window_id": "W0", "t0": 0.0, "t1": 4.5,
            "analisis_tactico": r_ok["analisis_tactico"],
            "narracion_es": "Costa Rica juega adelantado a setenta metros de su portería.",
        }
        res_b4 = mon_b.audit_call(REQUIRED_MODEL, "W0", r_num_letras, 10.0, 100, 40, mode="online")

        ok_b = (
            res_b1["status"] == "FAIL" and not res_b1["checks"]["numbers_accuracy"]["pass"]
            and res_b2["status"] == "PASS"
            and res_b3["status"] == "FAIL" and not res_b3["checks"]["narration_length"]["pass"]
            and res_b3["checks"]["narration_length"]["word_count"] == 19
            and res_b4["status"] == "FAIL"
            and any("escribe las cifras con dígitos" in e for e in res_b4["errors"])
        )
        registrar(
            "b. Número del equipo equivocado -> FAIL; 'presencia' -> PASS; 19 palabras -> FAIL; cifra en letras -> FAIL",
            ok_b,
            f"num_cruzado={res_b1['status']}, presencia={res_b2['status']}, 19_palabras={res_b3['status']}, num_letras={res_b4['status']}",
        )

        # ── c. Las 8 frases viejas de data/clean/narrations.json contra las reglas nuevas
        with open(CLEAN_DIR / "narrations.json", "r", encoding="utf-8") as f:
            viejas = json.load(f)

        mon_c = GovernanceMonitorM3(tactical_real, audit_log=tmp / "audit_c.jsonl")
        fallos_viejas = []
        print("\n  --- Evaluación de las 8 crónicas viejas (data/clean/narrations.json) ---")
        for nv in viejas:
            wid = nv["window_id"]
            aud = mon_c.audit_call(
                REQUIRED_MODEL,
                wid,
                {k: nv[k] for k in ("window_id", "t0", "t1", "analisis_tactico", "narracion_es")},
                nv.get("latency_ms", 0.0),
                nv.get("tokens_in", 0),
                nv.get("tokens_out", 0),
                mode="online",
            )
            if aud["status"] == "FAIL":
                fallos_viejas.append(wid)
            motivos = "; ".join(aud["errors"]) if aud["errors"] else "OK"
            print(f"    {wid}: {aud['status']} -> {motivos}")
        print("  ------------------------------------------------------------------------\n")

        ok_c = len(viejas) == 8 and not fallos_viejas
        registrar(
            "c. Las 8 frases publicadas en data/clean/narrations.json pasan M3",
            ok_c,
            f"fallaron {len(fallos_viejas)}/{len(viejas)} ({', '.join(fallos_viejas) or 'ninguna'})",
        )

        # ── d. La plantilla offline de las 8 ventanas reales pasa M3 ─────────
        mon_d = GovernanceMonitorM3(tactical_real, audit_log=tmp / "audit_d.jsonl")
        frases_offline = []
        for w in tactical_real:
            off_res, lat, tin, tout = narr._generate_offline_narration(w)
            frases_offline.append(off_res)
            mon_d.audit_call(
                REQUIRED_MODEL,
                w["window_id"],
                off_res,
                lat,
                tin,
                tout,
                mode="offline",
            )
        rep_d = mon_d.finalize_report(report_path=tmp / "report_d.json")
        ok_d = (
            rep_d["status"] == "PASS"
            and rep_d["summary"]["passed_calls"] == 8
            and rep_d["summary"]["offline_calls"] == 8
            and rep_d["summary"]["online_calls"] == 0
            and rep_d["summary"]["total_cost_ru_est"] == 0.0
        )
        registrar(
            "d. Plantilla offline de las 8 ventanas reales pasa M3 (costo 0 RU)",
            ok_d,
            f"status={rep_d['status']}, passed={rep_d['summary']['passed_calls']}/8, cost_ru={rep_d['summary']['total_cost_ru_est']}",
        )

        # ── e. Modelo falso que falla 1 vez y acierta (2 intentos, PASS, retries) y otro que falla siempre (offline)
        tact_1w_path = tmp / "tact_1w.json"
        tact_1w_path.write_text(json.dumps([w0], ensure_ascii=False), encoding="utf-8")

        fake_retry_model = _FakeModelFailOnceThenPass({"W0": frases_offline[0]})
        res_e1 = narr.run_agent_narrator(
            tactical_path=tact_1w_path,
            narrations_path=tmp / "narr_e1.json",
            audit_log=tmp / "audit_e1.jsonl",
            report_path=tmp / "report_e1.json",
            model_override=fake_retry_model,
        )
        entries_e1 = [json.loads(l) for l in (tmp / "audit_e1.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

        fake_fail_model = _FakeModelAlwaysFail()
        res_e2 = narr.run_agent_narrator(
            tactical_path=tact_1w_path,
            narrations_path=tmp / "narr_e2.json",
            audit_log=tmp / "audit_e2.jsonl",
            report_path=tmp / "report_e2.json",
            model_override=fake_fail_model,
        )
        entries_e2 = [json.loads(l) for l in (tmp / "audit_e2.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

        ok_e = (
            res_e1["status"] == "PASS"
            and res_e1["mode"] == "online"
            and len(entries_e1) == 2
            and entries_e1[0]["status"] == "FAIL"
            and entries_e1[1]["status"] == "PASS"
            and res_e1["m3_report"]["summary"]["retries"] == 1
            and res_e1["m3_report"]["summary"]["online_calls"] == 1
            and res_e1["m3_report"]["summary"]["offline_calls"] == 0
            and "warning" not in res_e1["m3_report"]["summary"]
            and "rechazado por el monitor M3" in fake_retry_model.last_prompt_by_w.get("W0", "")
            and res_e2["status"] == "PASS"
            and res_e2["mode"] == "offline"
            and res_e2["narrations"][0]["mode"] == "offline"
            and len(entries_e2) == 4  # 3 intentos online fallidos + 1 fallback offline PASS
            and entries_e2[-1]["cost_ru_est"] == 0.0
            and res_e2["m3_report"]["summary"]["online_calls"] == 0
            and res_e2["m3_report"]["summary"]["offline_calls"] == 1
            and "WARNING" in str(res_e2["m3_report"]["summary"].get("warning", ""))
        )
        registrar(
            "e. Reintentos con Granite (1 fallo + 1 acierto -> 2 intentos, PASS; fallo siempre -> offline con WARNING y 0 RU)",
            ok_e,
            f"caso1(intentos={len(entries_e1)}, retries={res_e1['m3_report']['summary']['retries']}, online={res_e1['m3_report']['summary']['online_calls']}, status={res_e1['status']}), "
            f"caso2(intentos={len(entries_e2)}, offline={res_e2['m3_report']['summary']['offline_calls']}, warn={bool(res_e2['m3_report']['summary'].get('warning'))}, status={res_e2['status']})",
        )

        # ── f. Modelo no Granite -> FAIL ─────────────────────────────────────
        mon_f = GovernanceMonitorM3([w0], audit_log=tmp / "audit_f.jsonl")
        res_f = mon_f.audit_call("gpt-4o", "W0", r_ok, 10.0, 100, 40, mode="online")
        rep_f = mon_f.finalize_report(report_path=tmp / "report_f.json")
        ok_f = (res_f["status"] == "FAIL") and (not res_f["checks"]["model_id"]["pass"]) and (rep_f["status"] == "FAIL")
        registrar(
            "f. Modelo no Granite ('gpt-4o') -> FAIL",
            ok_f,
            f"call_status={res_f['status']}, model_check={res_f['checks']['model_id']['pass']}, report_status={rep_f['status']}",
        )

        # ── g. Exportador en carpeta temporal: sin NaN ni claves viejas, árbitros team=2, y rastro 29 con SKN en 600 y CRC en 800
        orig_out_data = exp_dash.OUT_DATA
        orig_out_partido = exp_dash.OUT_PARTIDO
        orig_out_media = exp_dash.OUT_MEDIA
        orig_argv = sys.argv[:]
        try:
            exp_dash.OUT_DATA = tmp / "dash_data"
            exp_dash.OUT_PARTIDO = exp_dash.OUT_DATA / "partido"
            exp_dash.OUT_MEDIA = tmp / "dash_media"
            sys.argv = ["export_dashboard_data.py", "--no-media"]
            exp_dash.main()
        finally:
            exp_dash.OUT_DATA = orig_out_data
            exp_dash.OUT_PARTIDO = orig_out_partido
            exp_dash.OUT_MEDIA = orig_out_media
            sys.argv = orig_argv

        mateo_txt = (tmp / "dash_data" / "mateo_data.json").read_text(encoding="utf-8")
        metodo_txt = (tmp / "dash_data" / "metodo.json").read_text(encoding="utf-8")
        mateo_d = json.loads(mateo_txt)
        metodo_d = json.loads(metodo_txt)

        claves_viejas = {"block_height_m", "compactness_m", "transition_mps", "pressure"}
        tiene_claves_viejas = any(
            bool(claves_viejas & set(w.keys())) for w in mateo_d["windows"]
        )
        tiene_nuevas = all(
            ("territorio" in w and "equipos" in w) for w in mateo_d["windows"]
        )
        tiene_radar_err = (
            isinstance(metodo_d.get("radar_error"), dict)
            and metodo_d["radar_error"].get("metodo") == "área grande sin usarla para calibrar"
        )

        # Revisar rastro 29 en cuadro 600 (W4 -> team 0 = SKN) y en cuadro 800 (W5 -> team 1 = CRC)
        p_600 = {row[0]: row[1] for row in mateo_d["frames"][600]["p"]}
        p_800 = {row[0]: row[1] for row in mateo_d["frames"][800]["p"]}
        t29_600 = p_600.get(29)
        t29_800 = p_800.get(29)
        # Los árbitros por moda del tramo se exportan con team == 2
        hay_arbitros_en_radar = any(
            any(row[1] == 2 for row in fr["p"]) for fr in mateo_d["frames"]
        )

        ok_g = (
            "NaN" not in mateo_txt
            and "NaN" not in metodo_txt
            and not tiene_claves_viejas
            and tiene_nuevas
            and tiene_radar_err
            and t29_600 == 0
            and t29_800 == 1
            and hay_arbitros_en_radar
        )
        registrar(
            "g. Exportador en carpeta temporal: sin NaN ni claves viejas, radar_error en metodo.json, árbitros team=2, rastro 29 SKN(600)->CRC(800)",
            ok_g,
            f"claves_viejas={tiene_claves_viejas}, nuevas={tiene_nuevas}, radar_error={tiene_radar_err}, "
            f"rastro29(f600={t29_600}[SKN=0], f800={t29_800}[CRC=1]), arbitros_team2={hay_arbitros_en_radar}",
        )

        # ── h. Las 5 frases FAIL y 3 frases (2 PASS + 1 FAIL por "encierra") de C3a.1
        w1 = tactical_real[1]  # W1: territorio="repartido"
        mon_h = GovernanceMonitorM3([w0, w1], audit_log=tmp / "audit_h.jsonl")

        analisis_w0_ok = r_ok["analisis_tactico"]
        analisis_w1_ok = frases_offline[1]["analisis_tactico"]

        casos_h = [
            ("W0", analisis_w0_ok, "Costa Rica se repliega en su mitad.", "FAIL", None),
            ("W0", analisis_w0_ok, "San Cristóbal y Nieves avanza y empuja a Costa Rica atrás.", "FAIL", None),
            ("W0", analisis_w0_ok, "Costa Rica busca el gol con insistencia.", "FAIL", None),
            ("W0", analisis_w0_ok, "San Cristóbal y Nieves ataca mientras Costa Rica espera.", "FAIL", None),
            ("W0", analisis_w0_ok, "San Cristóbal y Nieves, sin espacio atrás, juega adelantado.", "FAIL", None),
            ("W0", analisis_w0_ok, "El presidente mira; Costa Rica juega adelantada.", "PASS", None),
            ("W1", analisis_w1_ok, "Territorio repartido entre San Cristóbal y Nieves y Costa Rica.", "PASS", None),
            ("W0", analisis_w0_ok, "Costa Rica pisa campo rival y San Cristóbal y Nieves se encierra atrás.", "FAIL", "encierra"),
        ]

        detalles_h = []
        ok_h = True
        for idx_h, (wid_h, ana_h, frase_h, esp_h, palabra_esp) in enumerate(casos_h, start=1):
            w_ref = w0 if wid_h == "W0" else w1
            resp_h = {
                "window_id": wid_h,
                "t0": w_ref["t0"],
                "t1": w_ref["t1"],
                "analisis_tactico": ana_h,
                "narracion_es": frase_h,
            }
            aud_h = mon_h.audit_call(REQUIRED_MODEL, wid_h, resp_h, 10.0, 100, 40, mode="online")
            cumple = aud_h["status"] == esp_h
            if palabra_esp is not None:
                cumple = cumple and (palabra_esp in aud_h["checks"]["forbidden_words"]["found"])
            if not cumple:
                ok_h = False
            detalles_h.append(f"#{idx_h}:{aud_h['status']}(esp:{esp_h})")

        registrar(
            "h. 8 frases de prueba C3a.1 (5 FAIL + 2 PASS + 1 FAIL por 'encierra')",
            ok_h,
            ", ".join(detalles_h),
        )

        # ── i. Huecos de M3 cerrados (26/11) ─────────────────────────────────
        mon_i = GovernanceMonitorM3(tactical_real, audit_log=tmp / "audit_i.jsonl")
        por_id = {w["window_id"]: w for w in tactical_real}
        casos_i = [
            ("W0", "San Cristóbal y Nieves se ubica a 37 m de su portería. Costa Rica se ubica a 70 m de su portería.",
             "Territorio repartido: ninguno de los dos equipos ocupa claramente más campo rival.", "FAIL"),
            ("W0", "San Cristóbal y Nieves se ubica a 37 m de su portería. Costa Rica se ubica a 70 m de su portería.",
             "Un equipo juega adelantado y el otro queda atrás.", "FAIL"),
            ("W1", "San Cristóbal y Nieves se ubica a 53 m de su portería. Costa Rica se encuentra en la mitad rival, a 48 m de su portería.",
             "Costa Rica se encuentra en la mitad rival.", "FAIL"),
            ("W3", "San Cristóbal y Nieves se ubica a 50 m de su portería. Costa Rica se ubica a 48 m.",
             "Costa Rica se instala en campo rival.", "FAIL"),
            ("W0", "San Cristóbal y Nieves se ubica a 37 m. Costa Rica se ubica a 70 m.",
             "Costa Rica queda en su mitad.", "FAIL"),
            ("W0", "San Cristóbal y Nieves se ubica a 37 m. Costa Rica se ubica a 70 m.",
             "Costa Rica sube sus líneas.", "FAIL"),
            ("W0", "San Cristóbal y Nieves se ubica a 37 m. Costa Rica se ubica a 70 m.",
             "Costa Rica adelantado; San Cristóbal y Nieves se retrasa.", "FAIL"),
            ("W0", "San Cristóbal y Nieves se ubica a 37 m. Costa Rica tiene 88 por ciento en campo rival.",
             "Costa Rica juega adelantado, con 88 por ciento en campo rival.", "PASS"),
            ("W1", "San Cristóbal y Nieves se ubica a 53 m. Costa Rica se ubica a 48 m.",
             "Costa Rica no llega a la mitad rival; territorio repartido.", "PASS"),
            ("W2", "San Cristóbal y Nieves se ubica a 55 m de su portería, en la mitad rival. Costa Rica se ubica en su mitad, a 41 m.",
             "San Cristóbal y Nieves juega en la mitad rival; Costa Rica queda en su mitad.", "PASS"),
            ("W0", "San Cristóbal y Nieves se ubica a 37 m. Costa Rica se ubica a 70 m, ocupando el 88% del territorio.",
             "Costa Rica adelantado, San Cristóbal y Nieves en su mitad.", "FAIL"),
            ("W0", "San Cristóbal y Nieves se ubica a 37 m, ocupando un espacio de 6% en campo rival. Costa Rica se ubica a 70 m.",
             "Costa Rica adelantado, San Cristóbal y Nieves en su mitad.", "FAIL"),
            ("W6", "San Cristóbal y Nieves se ubica a 35 m. Costa Rica se ubica a 61 m.",
             "Costa Rica adelantado, 61 metros; San Cristóbal y Nieves en mitad.", "FAIL"),
        ]
        ok_i = True
        detalles_i = []
        for idx_i, (wid, ana, nar, esp_i) in enumerate(casos_i, start=1):
            w = por_id[wid]
            aud_i = mon_i.audit_call(
                REQUIRED_MODEL, wid,
                {"window_id": wid, "t0": w["t0"], "t1": w["t1"], "analisis_tactico": ana, "narracion_es": nar},
                10.0, 100, 40, mode="online",
            )
            if aud_i["status"] != esp_i:
                ok_i = False
            detalles_i.append(f"#{idx_i}:{aud_i['status']}(esp:{esp_i})")
        registrar(
            "i. Huecos de M3 cerrados: nombrar territorio, mitad rival / su mitad contra el %, 'sube sus líneas', 'por ciento', redacción del %",
            ok_i,
            ", ".join(detalles_i),
        )

    print("\n  --- Las 8 frases offline generadas por la plantilla nueva ---")
    for fr in frases_offline:
        pal = len(fr["narracion_es"].split())
        print(f"    [{fr['window_id']}] ({pal} pal.) narracion_es: {fr['narracion_es']}")
        print(f"         analisis_tactico: {fr['analisis_tactico']}")
    print("  -------------------------------------------------------------\n")

    print("-" * 80)
    n_ok = sum(1 for _, ok, _ in resultados if ok)
    n_total = len(resultados)
    print(f"  Resultado: {n_ok}/{n_total} pruebas superadas")
    print("=" * 80)
    return 0 if n_ok == n_total else 1


if __name__ == "__main__":
    raise SystemExit(main())
