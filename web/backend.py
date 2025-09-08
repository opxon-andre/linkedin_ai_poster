import sys
import os
import configparser
import json
import threading
import time

sys.path.append(os.path.join(os.path.dirname(sys.path[0])))
import app.config as cfg
from app.linkedin_bot import web_post_existing_html
from app.utils import get_schedules_from_post, generate_text, generate_image, save_post_as_html, edit_prompt, create_and_save_post, extract_post_elements

import contenteditor_functions as ccf

from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime



CONTENT_DIR = Path(f"{os.getcwd()}/content/new")
CONFIG_FILE = f"{os.getcwd()}/config/config.ini"
'''
config = configparser.ConfigParser()
config.read(CONFIG_FILE)

promptfile = config["PROMPTS"]["text_file"]
promptpath = Path(f"{os.getcwd()}/config/{promptfile}")
'''

webapp = Flask(__name__, static_folder="../content")

# Status-Speicher für Hintergrundjobs
generation_status = {"running": False, "finished": False}


###########################################################################################################
### Handling of postings for linkedin

def get_all_posts():
    return [f for f in os.listdir(CONTENT_DIR) if f.endswith(".html")]



def load_templates():
    dir = Path(f"{os.getcwd()}/content/templates")
    if not os.path.isfile(Path(f"{os.getcwd()}/content/new/template.html")):
        file = generate_new_template()
        print(f"New template generated: {file}")
        os.rename(file, f"{os.getcwd()}/content/new/template.html")
    return load_posts(ending="template.html")




def load_posts(read_dir=None, ending="post_*.html"):
    if not read_dir:
        read_dir = CONTENT_DIR

    print(f"read_dir: {read_dir}")
    posts = []
    for file in read_dir.glob(ending):
        with open(file, "r", encoding="utf-8") as f:

            soup = BeautifulSoup(f, "html.parser")
            
            title = soup.find("h1").text if soup.find("h1") else file.stem

            # Confirmed-Flag auslesen
            confirmed_span = soup.find("span", {"class": "confirmed"})
            confirmed = confirmed_span.text.strip() if confirmed_span else "No"

            # origin (author) lesen
            origin_span = soup.find("span", {"class": "origin"}) 
            origin = origin_span.text.strip() if origin_span else "company" #config["TEMPLATES"]["post_as"]

            # Posting-History auslesen
            history = []
            meta_section = soup.find("section", {"class": "posting-meta"})
            if meta_section:
                for entry in meta_section.find_all("div", {"class": "post-log"}):
                    platform = entry.find("span", {"class": "platform"})
                    timestamp = entry.find("span", {"class": "timestamp"})
                    history.append({
                        "platform": platform.text.strip() if platform else "unknown",
                        "timestamp": timestamp.text.strip() if timestamp else "unknown"
                    })

            # Schedule auslesen
            schedule = get_schedules_from_post(file)

            posts.append({
                "filename": file.name,
                "title": title,
                "confirmed": confirmed,
                "history": history,
                "schedule" : schedule,
                "origin":origin
            })
    return posts


    
############################
## toggle confirmed Flag
@webapp.route("/update_flag", methods=["POST"])
def update_flag():
    data = request.json
    #print("Data: ",data["confirmed"])
    filename = data["filename"]
    new_flag = data["confirmed"] if data["confirmed"] else "No"
    #print(f"New confirmation: ", new_flag)

    file_path = CONTENT_DIR / filename
    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    confirmed_span = soup.find("span", {"class": "confirmed"})
    if confirmed_span:
        confirmed_span.string = new_flag

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(soup))

    return jsonify(success=True, new_flag=new_flag)


############################
## toggle origin/author between personal and company
@webapp.route("/change_origin", methods=["POST"])
def change_origin():
    data = request.json
    #print("Data: ",data["origin"])
    filename = data["filename"]
    new_flag = data["origin"] if data["origin"] else "Company"
    #print(f"New origin: ", new_flag)

    file_path = CONTENT_DIR / filename
    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    span = soup.find("span", {"class": "origin"})
    if span:
        span.string = new_flag

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(soup))

    return jsonify(success=True, new_flag=new_flag)



@webapp.route("/post_now", methods=["POST"])
def post_now():
    data = request.json
    filename = data["filename"]
    file_path = CONTENT_DIR / filename
    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

        # Confirmed-Flag auslesen
        confirmed_span = soup.find("span", {"class": "confirmed"})
        confirmed = confirmed_span.text.strip() 
        if confirmed == "Yes":
            try:
                resp, link = web_post_existing_html(file_path)
                return jsonify(success=True, link=link), resp
            except Exception as e:
                return jsonify({"error": str(e)}), resp
        else:
            return jsonify(success=False), 300




@webapp.route("/delete_post", methods=["POST"])
def delete_post():
    data = request.get_json()
    filename = data.get("filename")

    if not filename:
        return jsonify({"error": "Filename missing"}), 400

    file_path = os.path.join(CONTENT_DIR, filename)

    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    try:
        os.remove(file_path)
        return jsonify({"status": "success", "filename": filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 500





##########################################################################################
### Scheduler for prepared postings


@webapp.route("/scheduler", methods=["GET", "POST"])
def scheduler():
    filename = request.args.get("filename")
    filepath = os.path.join(CONTENT_DIR, filename)
    all_files = get_all_posts()
    schedules = get_schedules_from_post(filepath)

    return render_template("scheduler.html",
                           filename=filename,
                           all_files=all_files,
                           schedules=schedules)



@webapp.route("/save_schedule", methods=["POST"])
def save_schedule():
    filename = request.form["filename"]
    datetime_val = request.form["datetime"]
    repeat_val = request.form.get("repeat", "")

    filepath = os.path.join(CONTENT_DIR, filename)
    if not os.path.exists(filepath):
        return f"File {filename} not found", 404

    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    meta = soup.select_one("section.posting-meta")
    if not meta:
        meta = soup.new_tag("section", **{"class": "posting-meta"})
        soup.body.insert(0, meta)

    # neuen Schedule ergänzen
    new_span = soup.new_tag("span", **{
        "class": "schedule",
        "data-datetime": datetime_val,
        "data-repeat": repeat_val
    })
    meta.append(new_span)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(str(soup))

    return redirect(url_for("scheduler", filename=filename))



@webapp.route("/delete_schedule", methods=["POST"])
def delete_schedule():
    filename = request.form["filename"]
    datetime_val = request.form["datetime"]

    filepath = os.path.join(CONTENT_DIR, filename)
    if not os.path.exists(filepath):
        return f"File {filename} not found", 404

    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    # passenden Eintrag löschen
    for span in soup.select("section.posting-meta span.schedule"):
        if span.get("data-datetime") == datetime_val:
            span.decompose()

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(str(soup))

    return redirect(url_for("scheduler", filename=filename))



@webapp.route("/schedule_submit", methods=["POST"])
def schedule_submit():
    filename = request.form.get("filename")
    run_date = request.form.get("run_date")
    cron_hour = request.form.get("cron_hour")
    cron_minute = request.form.get("cron_minute")
    cron_dow = request.form.get("cron_dow")

    cron = None
    if cron_hour or cron_minute or cron_dow:
        cron = {
            "hour": cron_hour or "*",
            "minute": cron_minute or "0",
            "day_of_week": cron_dow or "*"
        }

    # Call API intern statt curl
    with webapp.test_client() as c:
        payload = {"filename": filename}
        if run_date:
            payload["run_date"] = run_date
        if cron:
            payload["cron"] = cron
        c.post("/save_schedule", json=payload)

    return redirect(url_for("scheduler_ui"))


#####################################################################################
### update single cards (for reload after change in schedule, text or postings)


@webapp.route("/card/<filename>")
def get_card(filename):
    file_path = os.path.join("content", "new", filename)
    if not os.path.exists(file_path):
        return "Not found", 404
    
    with open(file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Du kannst das in ein Partial-Template packen,
    # aber erstmal direkt zurückgeben:
    return html_content


#####################################################################################
### Prompt handling

def load_prompts():
    prompts = []
    if not os.path.exists(cfg.promptpath):
        raise FileNotFoundError(f"File not found: {cfg.promptpath}")

    with open(cfg.promptpath, 'r', encoding="utf-8") as file:
        for line in file:
            prompts.append(line.strip())

    return prompts



@webapp.route("/generate_new", methods=["POST"])
def generate_new():
    prompt = request.form.get("prompt")

    text = generate_text(prompt)
    if not text:
        print("Text generation failed - aborting!")
        exit()
    else:
        print("Text generation successful!\n")
        
    image_url = generate_image(text)
    html_file = save_post_as_html(text, image_url)
    fqdp = Path(html_file)
    print(f"Post als HTML gespeichert: {fqdp}")
    return jsonify({"status": "success"})




@webapp.route("/edit_prompt")
def prompts_page():
    old_text = request.args.get("prompt", "")
    print("Übergabe an promptedit:\n", old_text)
    return render_template("prompts.html", old_text=old_text)




def update_prompt_in_file(old_text, new_text):
    """Ersetzt eine Zeile oder fügt neue hinzu, wenn old_text leer ist."""
    try:
        with open(cfg.promptpath, "r", encoding="utf-8") as f:
            lines = [line.rstrip("\n") for line in f]

        updated = False
        new_lines = []
        for line in lines:
            if line == old_text:
                new_lines.append(new_text)
                updated = True
            else:
                new_lines.append(line)

        if not updated:
            # neuer Eintrag, falls old_text leer war oder nicht existierte
            new_lines.append(new_text)

        with open(cfg.promptpath, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines) + "\n")

        return True
    except Exception as e:
        print("Fehler beim Speichern:", e)
        return False


@webapp.route("/save_prompt", methods=["POST"])
def save_prompt():
    old_text = request.form.get("old_text", "").strip()
    new_text = request.form.get("new_text", "").strip()

    success = update_prompt_in_file(old_text, new_text)

    return jsonify({
        "success": success,
        "new_text": new_text
    })




def a_create_content(prompt):
    global generation_status
    generation_status["running"] = True
    generation_status["finished"] = False

    # hier kommt dein eigentlicher Code hin:
    #time.sleep(120)  # simuliert deine 2 Minuten Generierung
    #filename = "new_post.html"
    #with open(os.path.join("content", "new", filename), "w", encoding="utf-8") as f:
    #    f.write("<html><body><h1>Neues Posting</h1></body></html>")

    ## calling function in utils
    ret, file = create_and_save_post(prompt)

    generation_status["running"] = False
    generation_status["finished"] = True


@webapp.route("/generate_new_content", methods=["POST"])
def generate_new_content():
    data = request.get_json()
    prompt = data.get("prompt", "")
    t = threading.Thread(target=a_create_content, args=(prompt,))
    t.start()
    return jsonify({"status": "started", "prompt": prompt})


@webapp.route("/check_status")
def check_status():
    return jsonify(generation_status)


#######################################################################################
### Functions for Config-management

def read_config(file_path=CONFIG_FILE):
    """Read the configuration file and handle quoted/unquoted values."""
    config = configparser.ConfigParser()

    # Enable case-sensitive options (optional)
    config.optionxform = str

    # Read the configuration file
    config.read(file_path)

    # Strip quotes from values
    parsed_config = {
        section: {
            key: value.strip('"').strip("'")  # Remove both double and single quotes
            for key, value in config.items(section)
        }
        for section in config.sections()
    }
    return parsed_config


def write_config(config, file_path=CONFIG_FILE):
    """Write the configuration to a file, preserving quotes around values."""
    parser = configparser.ConfigParser()
    for section, options in config.items():
        parser[section] = {
            key: f'"{value}"' if not (value.startswith('"') and value.endswith('"')) else value
            for key, value in options.items()
        }
    with open(file_path, "w") as configfile:
        parser.write(configfile)


#######################################################################
### Pages and actions for Config-management

@webapp.route("/config")
def conf_index():
    """Serve the main Web UI for configs."""
    config_data = read_config()  
    #return render_template("config_index.html", config=json.dumps(config_data))
    return render_template("config_index.html", config=config_data)


@webapp.route("/config/update", methods=["POST"])
def config_update():
    """Update the configuration file."""
    updated_config = request.json
    write_config(updated_config)
    return jsonify({"status": "success"}), 200


@webapp.route("/config/save", methods=["POST"])
def config_save():
    try:
        updated_config = request.json
        write_config(updated_config)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500



#####################################################################################
### Custom content creator

@webapp.route("/new_custom", methods=["POST"])
def new_custom_content():
    filename = request.form.get("filename")
    print(f"Filename: {request.form}")
    filepath = os.path.join(CONTENT_DIR, filename)
    return render_template("custom.html", filepath=filepath)



def generate_new_template():
    text = "Create something custom"
    image_url = "https://picsum.photos/200/300"
    html_file = save_post_as_html(text, image_url)
    return html_file



@webapp.route("/custom_creator")
def custom_creator():
    return render_template("custom_creator.html")

@webapp.route("/save_custom_post", methods=["POST"])
def save_custom_post():
    data = request.get_json()
    html = data.get("html", "")

    if not html.strip():
        return jsonify({"success": False, "error": "Empty HTML"})

    # Dateiname mit Timestamp
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"post_{ts}.html"
    file_path = os.path.join(CONTENT_DIR, filename)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html)
        return jsonify({"success": True, "filename": filename})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    



#####################################################################################
## Custom Creator alternative

@webapp.route('/contenteditor')
def content_editor():
    return render_template('content_editor_2.html')


@webapp.route('/api/file-info')
def api_file_info():
    return ccf.api_file_info()


@webapp.route('/api/save', methods=['POST'])
def api_save():
    return ccf.api_save()


@webapp.route('/api/preview', methods=['POST'])
def api_preview():
    return ccf.api_preview()


@webapp.route('/api/extract-elements')
def api_extract_elements():
    return ccf.api_extract_elements()

#####################################################################################
#### Static 

# Statische Dateien verfügbar machen
@webapp.route('/content/new/<path:filename>')
def serve_postings(filename):
    return send_from_directory("../content/new", filename)


@webapp.route('/content/images/<path:filename>')
def serve_images(filename):
    return send_from_directory("../content/images", filename)


@webapp.route('/content/static/icons/<path:filename>')
def serve_icon(filename):
    return send_from_directory("../content/static/icons", filename)



@webapp.route("/")
def index():
    templates = load_templates()
    posts = load_posts()
    prompts = load_prompts()
    return render_template("index.html", posts=posts, prompts=prompts, templates=templates)




if __name__ == "__main__":
    #webapp.run(debug=True)
    webapp.run(host='0.0.0.0', port=4561, debug=True)
    #confapp.run(host='0.0.0.0', port=4560, debug=True)
