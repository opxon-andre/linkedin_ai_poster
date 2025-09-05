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



def run_scheduler(interval=60):
    scheduler.scheduler(interval)  # jede Minute prüfen


def run_flask():
    webapp.run(host="0.0.0.0", port=4561)







# --- Hauptablauf Content generation---
def create_and_save_post(dry_run=True):
    text = ""
    text = utils.generate_text()
    if not text:
        print("Text generation failed - aborting!")
        exit()

    image_url = utils.generate_image(text)
    html_file = utils.save_post_as_html(text, image_url)
    fqdp = Path(html_file)
    print(f"Post als HTML gespeichert: {fqdp}")
    if not dry_run:
        resp = bot.post_to_linkedin(text, image_url, cfg.post_as)
        #print(f"Direkt auf LinkedIn gepostet: {resp}")






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
            print("Run scheduler and post when it´s time for it (Multithread)")
            # Scheduler in separatem Thread starten
            t = threading.Thread(target=run_scheduler, daemon=True)
            t.start()

            # Flask im Hauptthread starten
            run_flask()
            
        case _:
            dry = utils.get_dry_run()
            create_and_save_post(dry_run=dry)





if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    #execution_time = end_time - start_time
    #print(f"Execution time: {execution_time:.2f} seconds")
            