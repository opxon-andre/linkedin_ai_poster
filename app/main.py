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


log = utils.get_log(os.path.basename(__file__))


def run_scheduler(interval=60):
    log.info(f"run scheduler with an interval of {interval}s")
    scheduler.scheduler(interval)  # jede Minute prüfen


def run_flask():
    log.info("starting webapp on port 4561")
    webapp.run(host="0.0.0.0", port=4561)



def start():
    print("Run scheduler and post when it´s time for it (Multithread)")
    # Scheduler in separatem Thread starten
    t = threading.Thread(target=run_scheduler, daemon=True)
    t.start()

    # Flask im Hauptthread starten
    run_flask()



# --- Hauptablauf Content generation---
def create_and_save_post(dry_run=True):
    ret, file = utils.create_and_save_post()




def main(command=None):
    if command is None:
        parser = argparse.ArgumentParser()
        parser.add_argument("command")
        args = parser.parse_args()
        command = args.command

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
            start()
            
        case _:
            dry = utils.get_dry_run()
            create_and_save_post(dry_run=dry)





if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    #execution_time = end_time - start_time
    #print(f"Execution time: {execution_time:.2f} seconds")
            