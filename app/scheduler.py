import os
import sys
import time
import json
import ast
from datetime import datetime
from bs4 import BeautifulSoup

sys.path.append(os.path.join(os.path.dirname(sys.path[0])))
import utils
import linkedin_bot as bot
import app.config as cfg

# Verzeichnis mit den vorbereiteten Postings
SCHEDULE_DIR = cfg.output_dir

# -- Hilfsfunktionen --------------------------------------------------------

def parse_datetime_attr(s: str):
    """Robustes Parsen von data-datetime: akzeptiert ISO '2025-09-08T09:50' oder '2025-09-08 09:50' usw."""
    if not s:
        return None
    s = s.strip()
    try:
        # datetime.fromisoformat akzeptiert 'YYYY-MM-DDTHH:MM' und 'YYYY-MM-DD HH:MM'
        return datetime.fromisoformat(s)
    except Exception:
        formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M"]
        for fmt in formats:
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                pass
    return None


def parse_repeat_attr(s: str):
    """
    Parst data-repeat:
    - Wenn JSON (starts with '{') -> json.loads
    - sonst versucht ast.literal_eval (falls Python-dict-string)
    - sonst: liefert {"cron": "<raw string>"} (cron-like string)
    """
    if not s:
        return None
    s = s.strip()
    # JSON first
    if s.startswith("{") or s.startswith("["):
        try:
            return json.loads(s)
        except Exception:
            pass
    # try python literal (e.g. "{'hour': 9, 'minute': 0}")
    try:
        val = ast.literal_eval(s)
        if isinstance(val, dict):
            return val
    except Exception:
        pass
    # fallback -> treat as cron string
    return {"cron": s}


# day name --> weekday index (Mon=0 .. Sun=6)
_DOW_MAP = {"mon":0, "tue":1, "wed":2, "thu":3, "fri":4, "sat":5, "sun":6}


def dow_from_token(tok: str):
    tok = tok.strip().lower()
    if tok in _DOW_MAP:
        return _DOW_MAP[tok]
    if tok.isdigit():
        # accept 0-6 or 1-7 (map 1->0 if used)
        v = int(tok)
        if 0 <= v <= 6:
            return v
        if 1 <= v <= 7:
            return (v - 1) % 7
    return None


def matches_repeat_spec(spec, now: datetime) -> bool:
    """
    Prüft, ob 'now' mit dem Repeat-Spec übereinstimmt.
    Spec kann sein:
      - dict mit keys 'hour','minute','day_of_week' (Werte sind int oder strings wie 'mon-fri' oder '*')
      - dict {"cron": "MIN HOUR DOM MON DOW"} (5-field cron string) -> es werden minute/hour/dow verglichen
    Rückgabe True/False.
    """
    if not spec:
        return False

    # dict style (hour/minute/day_of_week)
    if isinstance(spec, dict) and ("hour" in spec or "minute" in spec or "day_of_week" in spec):
        # hour
        if "hour" in spec and spec["hour"] not in (None, "", "*"):
            try:
                if str(spec["hour"]) != "*" and int(spec["hour"]) != now.hour:
                    return False
            except Exception:
                # maybe 'mon-fri' misplacement -> ignore
                pass
        # minute
        if "minute" in spec and spec["minute"] not in (None, "", "*"):
            try:
                if str(spec["minute"]) != "*" and int(spec["minute"]) != now.minute:
                    return False
            except Exception:
                pass
        # day_of_week: support 'mon-fri', 'mon,tue', '*' or single names
        if "day_of_week" in spec and spec["day_of_week"] not in (None, "", "*"):
            dow_spec = str(spec["day_of_week"]).lower()
            # range 'mon-fri'
            if "-" in dow_spec:
                a,b = dow_spec.split("-", 1)
                a_idx = dow_from_token(a)
                b_idx = dow_from_token(b)
                if a_idx is not None and b_idx is not None:
                    # handle wrap-around
                    cur = now.weekday()
                    if not (a_idx <= cur <= b_idx):
                        return False
            elif "," in dow_spec:
                toks = [t.strip() for t in dow_spec.split(",")]
                toks_idx = [dow_from_token(t) for t in toks]
                if now.weekday() not in [i for i in toks_idx if i is not None]:
                    return False
            else:
                # single token
                idx = dow_from_token(dow_spec)
                if idx is not None and now.weekday() != idx:
                    return False
        # passed all checks
        return True

    # cron string style (5 fields)
    if isinstance(spec, dict) and "cron" in spec and isinstance(spec["cron"], str):
        cron = spec["cron"].strip()
        parts = cron.split()
        if len(parts) != 5:
            return False
        minute_tok, hour_tok, dom_tok, mon_tok, dow_tok = parts
        def match_tok(tok, val):
            if tok == "*" or tok == "*/1":
                return True
            # comma list
            if "," in tok:
                for piece in tok.split(","):
                    if match_tok(piece, val):
                        return True
                return False
            # range
            if "-" in tok:
                a,b = tok.split("-",1)
                return int(a) <= val <= int(b)
            # numeric
            try:
                return int(tok) == val
            except Exception:
                return False
        # minute and hour must match
        if not match_tok(minute_tok, now.minute):
            return False
        if not match_tok(hour_tok, now.hour):
            return False
        # dow: cron uses 0-6 (Sun=0) or 1-7; try to match both
        if dow_tok != "*" and dow_tok != "?":
            try:
                if match_tok(int(dow_tok), now.weekday()):
                    pass
                else:
                    # try mapping 1-7 to 0-6
                    if match_tok(int(dow_tok) % 7, now.weekday()):
                        pass
                    else:
                        return False
            except Exception:
                # not numeric - ignore for now
                return False
        return True

    # fallback: not understood => don't run
    return False


# -- Scheduler --------------------------------------------------------------

def scheduler(interval: int = 30):
    """
    Polling scheduler: prüft alle content/new/*.html auf <span class="schedule" data-datetime="..." data-repeat="...">
    - Wenn data-datetime gesetzt (ISO), prüft auf exakten Minutenvergleich (YYYY-MM-DD HH:MM) und führt post_existing_html(filename) aus.
    - Wenn data-repeat gesetzt, wird geprüft ob 'now' auf das Repeat passt (siehe matches_repeat_spec).
    - Nach Ausführung:
       * Einmal-Jobs werden aus der Datei entfernt (span.decompose()).
       * Wiederkehrende Jobs bekommen ein data-last-run="YYYY-MM-DDTHH:MM" attribut, damit sie nicht mehrfach in derselben Minute laufen.
    """
    print("[SCHEDULER] started, Directory:", SCHEDULE_DIR)
    while True:
        now = datetime.now()
        now_min_str = now.strftime("%Y-%m-%dT%H:%M")  # for last-run compare

        for filename in os.listdir(SCHEDULE_DIR):
            if not filename.endswith(".html"):
                continue
            file_path = os.path.join(SCHEDULE_DIR, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    soup = BeautifulSoup(f.read(), "html.parser")

                changed = False
                meta = soup.find("section", {"class": "posting-meta"})
                if not meta:
                    continue

                spans = meta.find_all("span", {"class": "schedule"})
                for span in spans:
                    dt_attr = span.get("data-datetime", "")  # e.g. "2025-09-08T09:50"
                    repeat_attr = span.get("data-repeat", "")  # e.g. '{"hour":9,"minute":0}' or cron string
                    last_run = span.get("data-last-run", "")

                    # skip if already run in this minute
                    if last_run and last_run.startswith(now_min_str):
                        continue

                    # parse datetime if present
                    dt = parse_datetime_attr(dt_attr) if dt_attr else None
                    repeat_spec = parse_repeat_attr(repeat_attr) if repeat_attr else None

                    should_run = False
                    # 1) one-off at exact minute
                    if dt and not repeat_spec:
                        # compare minute-precision
                        tn = now.strftime("%Y-%m-%d %H:%M")
                        tp = dt.strftime("%Y-%m-%d %H:%M")
                        if tn == tp:
                            should_run = True

                    # 2) repeating rule (dict or cron string)
                    elif repeat_spec:
                        try:
                            if matches_repeat_spec(repeat_spec, now):
                                should_run = True
                        except Exception as e:
                            print(f"[WARN] repeat parse error for {filename}: {e}")
                            should_run = False

                    if should_run:
                        print(f"[SCHEDULER] Trigger: {filename} (dt={dt_attr}, repeat={repeat_attr}) at {now}")
                        try:
                            # call your existing function that posts a saved HTML
                            bot.post_existing_html(f"{SCHEDULE_DIR}/{filename}")
                        except Exception as e:
                            print(f"[ERROR] Fehler beim Senden von {SCHEDULE_DIR}/{filename}: {e}")
                        else:
                            # after successful posting:
                            if not repeat_spec:
                                # einmal-job: entfernen
                                span.decompose()
                                changed = True
                            else:
                                # wiederkehrend: markiere last-run (minute precision)
                                span['data-last-run'] = now_min_str
                                changed = True

                # falls wir modifiziert haben, zurückschreiben
                if changed:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(str(soup))

            except Exception as e:
                print(f"[ERROR] Fehler beim Verarbeiten von {filename}: {e}")

        # sleep
        time.sleep(interval)
