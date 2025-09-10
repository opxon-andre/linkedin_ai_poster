import configparser
import requests
import datetime
import base64
import os
import random
import time
import random
import sys
import logging

from datetime import datetime
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

from pathlib import Path
from openai import OpenAI

sys.path.append(os.path.join(os.path.dirname(sys.path[0])))
import app.config as cfg



timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

openai_client = OpenAI(api_key=cfg.openai_token)



def get_log_BAK(name=None):
    """
    get a log handler
    hand over the result of os.path.basename(__file__) as name
    """
    if not name:
        name = os.path.basename(__file__)

    loglevel = cfg.loglevel.strip('"').strip("'")

    Path(cfg.logpath).mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(loglevel)
    fh = logging.FileHandler(f"{cfg.logpath}linkedinbot.log")
    fh.setLevel(loglevel)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger


def get_log(name: str = __name__, log_file: str = cfg.logpath) -> logging.Logger:
    """
    Returns a logger that logs to console and a file, without duplicating messages.
    """
    logger = logging.getLogger(name)
    logger.setLevel(cfg.loglevel)

    if not logger.hasHandlers():
        # --- Console handler ---
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(cfg.loglevel)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # --- File handler ---
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        fh = logging.FileHandler(log_file)
        fh.setLevel(cfg.loglevel)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


log = get_log(os.path.basename(__file__))



def get_dry_run():
    if cfg.dry_run is False:
        return False
    else:
        print("Dry Run enabled. Saving posts locally only. No automated posting.")
        return True
    




def random_text_prompt():
    if not cfg.text_prompt_file:
        return cfg.text_prompt
    else:
        with open(f"{os.getcwd()}/config/{cfg.text_prompt_file}", "r", encoding="utf-8") as f:
            rline = None
            for i, line in enumerate(f, 1):
                if random.randrange(i) == 0:  # Wahrscheinlichkeit 1/i
                    rline = line.strip()
    return rline




def scheduler():
    now = datetime.now(cfg.timezone).strftime("%H:%M")
    while not (cfg.post_start <= now <= cfg.post_end):
        print(f"⚠️ Nicht im Post-Zeitfenster (Start: {cfg.post_start} - End: {cfg.post_end} - now: {now}).")
        time.sleep(1*3)
    else:
        return True
    



def create_and_save_post(prompt=None):
    """
    Generate new content as html file.
    optional parameter: a prompt for the Text generator. 
    If no prompt is give, one will be random selceted from the Promptsfile (see config)
    """
    if prompt:
        log.info("Generating new content with given prompt")
        text = generate_text(prompt)
    else:
        log.info("Gnerate new content with random prompt")
        text = generate_text()
    if not text:
        print("Text generation failed - aborting!")
        return False, None
        
    
    image_url = generate_image(text)
    html_file = save_post_as_html(text, image_url)
    fqdp = Path(html_file)
    print(f"Post als HTML gespeichert: {fqdp}")
    log.info(f"New Post saved as {fqdp}")
    return True, html_file




def generate_text(prompt=None):
    print("AI in use for text: ", cfg.text_ai)
    log.info(f"AI in use for text: {cfg.text_ai}")
    if prompt:
        text_prompt = prompt
    else:
        print("select random prompt to generate Text")
        log.info("select random prompt to generate Text")
        text_prompt = random_text_prompt()
    
    if (cfg.text_ai == "claude"):
        text = generate_text_with_claude(text_prompt)
    else:
        text = generate_text_with_chatgpt(text_prompt)

    return text



# --- Claude Textgenerierung ---
def generate_text_with_claude(text_prompt):
    print("Erzeuge Text mit Claude AI...")

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": cfg.claude_api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    data = {
        "model": cfg.claude_model,
        "max_tokens": 500,
        "messages": [{"role": "user", "content": text_prompt}]
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()["content"][0]["text"]



def generate_text_with_chatgpt(text_prompt):
    if cfg.demo != "False":
        print("Demo-Mode is ON")
        log.warning("This is a Demo only. Switch off the Demo Flag in config.ini to get rid of this")
        return "This is a Demo only. Switch off the Demo Flag in config.ini to get rid of this"

    print("Generate content with ChatGPT...")
    log.info("Generate content with ChatGPT...")

    log.debug(f"Prompt for Text:  {text_prompt}")
    response = openai_client.chat.completions.create(
        model="gpt-5",  # aktuelles ChatGPT-Modell
        messages=[
            {"role": "system", "content":cfg.system_prompt},
            {"role": "user", "content": text_prompt}
        ],
        #max_tokens=500,
        #temperature=0.7
    )

    # Text aus der Antwort extrahieren
    return response.choices[0].message.content.strip()


# --- ChatGPT Prüfung ---
def check_text_with_chatgpt(text):
    print("Überprüfe erzeugten Text mit ChatGPT.")
    resp = openai_client.chat.completions.create(
        model=cfg.openai_model,
        messages=[
            {"role": "system", "content": cfg.check_prompt},
            {"role": "user", "content": text}
        ]
    )
    return resp.choices[0].message.content.strip()



def generate_image(text):
    if cfg.demo != False:
        log.warning("Demo-Mode is ON")
        return "https://picsum.photos/200/300"


    imagefile = f"{os.getcwd()}/content/images/post_{timestamp}.png"
    log.info(f"Create related Image: {imagefile}")
    response = openai_client.responses.create(
        model=cfg.openai_model,
        #size="1024x1024",
        input = f"{cfg.image_prompt}\n\nBezug zum Text: {text}", 
        tools=[{"type": "image_generation"}],
    )

    # Save the image to a file
    image_data = [
        output.result
        for output in response.output
        if output.type == "image_generation_call"
    ]

    if image_data:
        image_base64 = image_data[0]
        with open(imagefile, "wb") as f:
            f.write(base64.b64decode(image_base64))
    log.debug("Image generated.")
    return imagefile



# --- HTML-Post speichern ---
def save_post_as_html(text, image_url, file_path=None):
    if not file_path:   
        file_path=Path(f"{os.getcwd()}/content/new/post_{timestamp}.html")

    render_linkedin_preview(
        template_path=Path(f"{os.getcwd()}/content/templates/{cfg.linkedin_tpl}"),
        out_path=file_path,
        company_name=cfg.company_name,
        logo_url="https://media.licdn.com/dms/image/v2/D4E0BAQFItEUyPgxpAQ/company-logo_100_100/company-logo_100_100/0/1730797026509?e=1759968000&v=beta&t=CFhnhW0YAvXmRjxKGtBTe5XsFWSnvMAzK3mFevmu_hA",
        tagline=cfg.company_tagline,
        text=text,
        image_url=image_url,
        hashtags="",
        reactions=random.randint(20,500), comments=random.randint(1,50), shares=random.randint(0,10),
        confirmed="False", 
        origin=cfg.post_as
    )
    log.info(f"html preview created as {file_path}")
    return file_path


def move_to_used(src):
    # move from new to used in ../content
    print(f"Used File: ", src)
    #os.rename(src, dest)
    return True

# Only for CLI Mode
def list_existing_posts():
    files = list(cfg.output_dir.glob("post_*.html"))
    for i, f in enumerate(files):
        print(f"[{i}] {f.name}")
    return files





def render_linkedin_preview(template_path: str, out_path: str, *,
                            company_name: str, logo_url: str, tagline: str,
                            text: str, image_url: str, hashtags: str = "",
                            reactions, comments, shares, confirmed, origin,
                            timestamp=None):
    """Füllt das LinkedIn-Template mit Inhalten und speichert es als HTML."""
    html = Path(template_path).read_text(encoding="utf-8")
    timestamp = timestamp or datetime.now().strftime("%d.%m.%Y %H:%M")

    title, body = split_post_text(text)

    replacements = {
        "{{TITLE}}": title,
        "{{COMPANY_NAME}}": company_name,
        "{{COMPANY_LOGO_URL}}": logo_url or "",
        "{{COMPANY_TAGLINE}}": tagline or "Unternehmensbeitrag",
        "{{TIMESTAMP}}": timestamp,
        "{{POST_TEXT}}": text,
        "{{POST_IMAGE_URL}}": image_url or "",
        "{{POST_HASHTAGS}}": hashtags or "",
        "{{REACTIONS_COUNT}}": str(reactions),
        "{{COMMENTS_COUNT}}": str(comments),
        "{{SHARES_COUNT}}": str(shares),
        "{{CONFIRMED}}": confirmed or "No",
        "{{ORIGIN}}": origin or "Company",
    }

    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(html, encoding="utf-8")
    return out_path




def extract_post_elements(html_path: str) -> dict:
    """Liest die Post-Elemente aus einer gespeicherten HTML-Vorschau zurück."""
    soup = BeautifulSoup(Path(html_path).read_text(encoding="utf-8"), "html.parser")

    return {
        "company_name": soup.select_one(".company-name").get_text(strip=True),
        "logo_url": soup.select_one(".company-logo")["src"],
        "tagline": soup.select_one(".company-tagline").get_text(strip=True),
        "timestamp": soup.select_one(".timestamp").get_text(strip=True),
        "text": soup.select_one(".post-text").get_text("\n", strip=True),
        "image_url": soup.select_one(".post-image")["src"] if soup.select_one(".post-image") else "",
        "hashtags": soup.select_one(".hashtags").get_text(" ", strip=True),
        "reactions": int(soup.select_one(".reactions").get_text(strip=True).split()[0]),
        "comments": int(soup.select_one(".comments").get_text(strip=True).split()[0]),
        "shares": int(soup.select_one(".shares").get_text(strip=True).split()[0]),
        "confirmed": int(soup.select_one(".confirmed").get_text(strip=True).split()[0]),
    }




def split_post_text(full_text: str):
    """Splits the post text into title (first line) and body (rest)."""
    lines = full_text.strip().split("\n", 1)
    title = lines[0]
    body = lines[1] if len(lines) > 1 else ""
    return title, body




def get_schedules_from_post(filepath):
    """
    Liest alle gespeicherten Schedules aus einer HTML-Datei
    und gibt eine Liste von Dicts zurück.
    """
    
    if not os.path.exists(filepath):
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    schedules = []
    for span in soup.select("section.posting-meta span.schedule"):
        dt_raw = span.get("data-datetime")
        repeat_val = span.get("data-repeat", "")

        dt_fmt = dt_raw
        try:
            # Versuchen in lesbares Format umzuwandeln
            dt_obj = datetime.strptime(dt_raw, "%Y-%m-%dT%H:%M")
            dt_fmt = dt_obj.strftime("%d.%m.%Y %H:%M")
        except Exception:
            pass  # wenn Format nicht passt, Rohwert beibehalten

        schedules.append({
            "datetime": dt_raw,
            "datetime_fmt": dt_fmt,
            "repeat": repeat_val
        })

    return schedules



def edit_prompt(old_text: str, new_text: str):
    """
    Edit the Prompts in the promptsfile (from config.ini -> PROMPTS -> text_file)
    Params: existing prompt or empty for a new prompt, new or edited prompt 
    """

    if not os.path.exists(cfg.promptpath):
        open(cfg.promptpath, "w", encoding="utf-8").close()

    with open(cfg.promptpath, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines()]

    if old_text:
        updated = False
        for i, line in enumerate(lines):
            if line == old_text.strip():
                lines[i] = new_text.strip()
                updated = True
                break
        if not updated:
            lines.append(new_text.strip())
    else:
        lines.append(new_text.strip())

    with open(cfg.promptpath, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

    return True