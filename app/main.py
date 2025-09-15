import os
import datetime
import argparse
import time
import sys
import threading
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(sys.path[0])))
import app.config as cfg
import linkedin_bot as bot
import utils
import scheduler

from web.backend import webapp

threadlock = threading.Lock()

log = utils.get_log(os.path.basename(__file__))

def run_preflight():
    log_path = Path(cfg.logpath)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    content_path = Path(f"{os.getcwd()}/content/new")
    content_path.parent.mkdir(parents=True, exist_ok=True)




def run_scheduler(interval=60):
    log.info(f"run scheduler with an interval of {interval}s")
    with threadlock:
        scheduler.scheduler(interval)  # jede Minute prüfen


def run_flask():
    log.info("starting webapp on port 4561")
    webapp.run(host="0.0.0.0", port=4561)


def run_setup():
    log.info("Config is missing... running setup now")
    log.warning("Config is missing... running setup now")
    webapp.run(host="0.0.0.0", port=4562)




def start():
    ## Check if config File is available
    CONFIG_FILE = f"{os.getcwd()}/config/config.ini"
    if not os.path.exists(CONFIG_FILE):
        log.error("There is no config.ini file in /config/ \nConfigure the setting according to the Template First")
        run_setup()
        exit()

    print("Run scheduler and post when it´s time for it (Multithread)")
    # Scheduler in separatem Thread starten
    t1 = threading.Thread(target=run_scheduler, daemon=True)
    #t2 = threading.Thread(target=run_flask, daemon=True)
    t1.start()
    #t2.start()
    
    # Flask im Hauptthread starten
    run_flask()
    



# --- Hauptablauf Content generation---
def create_and_save_post(dry_run=True):
    ret, file = utils.create_and_save_post()




def main(command=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("command")
    args = parser.parse_args()

    if args.command: command = args.command       
    else: command = None

    match command:
        case "post_existing":
            posts = utils.list_existing_posts()
            idx = int(input("Wähle den Index des zu postenden HTML-Posts: "))
            resp = bot.post_existing_html(posts[idx])
            print("Post wurde auf LinkedIn veröffentlicht:", resp)
        
        case "generate":
            # pick a random one of the prompts from config/textprompts and generate content about that
            print("Content creation only. No posting to LinkedIn")
            create_and_save_post(dry_run=True)
            
        case "automode":
            print("Select the first post from the existing list, post it, and prepare a new post in the stack.")
            posts = utils.list_existing_posts()
            bot.post_existing_html(posts[0])
            create_and_save_post(dry_run=True)

        case "scheduler":
            log.info("Starting Scheduler from main")
            run_preflight()
            start()
            
        case _:
            log.info("Starting Scheduler from main (default)")
            run_preflight()
            start()






if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    #execution_time = end_time - start_time
    #print(f"Execution time: {execution_time:.2f} seconds")
            