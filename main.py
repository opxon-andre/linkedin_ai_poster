import threading
import sys
import os
#from app import app, scheduler  # Flask app und scheduler importieren
sys.path.append(os.path.join(os.path.dirname(sys.path[0])))

from app.main import scheduler
from web.backend import webapp 



def run_scheduler():
    scheduler(interval=60)  # jede Minute prüfen


def run_flask():
    webapp.run(host="0.0.0.0", port=4561)



if __name__ == "__main__":
    # Scheduler in separatem Thread starten
    t = threading.Thread(target=run_scheduler, daemon=True)
    t.start()

    # Flask im Hauptthread starten
    run_flask()