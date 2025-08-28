import configparser
import requests
import datetime
import base64

from pathlib import Path
from openai import OpenAI


# --- Konfiguration laden ---
config = configparser.ConfigParser()
config.read("../config/config.ini")

openai_token = config["API"]["openai_token"]
#openai_client = OpenAI(api_key=config["API"]["openai_token"])
claude_api_key = config["API"]["claude_token"]
linkedin_token = config["API"]["linkedin_token"]
company_urn = config["API"]["linkedin_company_urn"]
company_page_id = config["API"]["company_page_id"]
person_id = config["API"]["person_id"]


claude_model = config["API"]["claude_model"]
openai_model = config["API"]["openai_model"]

start_hour = int(config["SCHEDULER"]["post_start"])
end_hour = int(config["SCHEDULER"]["post_end"])


# --- Prompts laden ---
prompts = configparser.ConfigParser()
prompts.read("../config/prompts")

text_prompt = prompts["PROMPTS"]["text_prompt"]
image_prompt = prompts["PROMPTS"]["image_prompt"]


output_dir = Path("../content/new")
output_dir.mkdir(exist_ok=True)

used_dir = Path("../content/used")
used_dir.mkdir(exist_ok=True)

timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

openai_client = OpenAI(api_key=openai_token)


# --- Claude Textgenerierung ---
def generate_text_with_claude():
    print("Erzeuge Text mit Claude AI...")

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": claude_api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    data = {
        "model": claude_model,
        "max_tokens": 500,
        "messages": [{"role": "user", "content": text_prompt}]
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()["content"][0]["text"]



def generate_text_with_chatgpt():
    print("Erzeuge Text mit ChatGPT...")
    response = openai_client.chat.completions.create(
        model="gpt-5",  # aktuelles ChatGPT-Modell
        messages=[
            {"role": "system", "content": "Du bist ein erfahrener Marketing- und LinkedIn-Texter."},
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
        model=openai_model,
        messages=[
            {"role": "system", "content": "Prüfe, ob der Text für LinkedIn geeignet ist. Antworte nur mit 'OK' oder 'NICHT OK'."},
            {"role": "user", "content": text}
        ]
    )
    return resp.choices[0].message.content.strip()



def generate_image(text):
    imagefile = output_dir / f"post_{timestamp}.png"
    print(f"Erstelle passendes Bild: {imagefile}")
    response = openai_client.responses.create(
        model="gpt-4.1-mini",
        #size="1024x1024",
        input = f"{image_prompt}\n\nBezug zum Text: {text}", #   "Generate an image of gray tabby cat hugging an otter with an orange scarf",
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
    
    return imagefile



# --- HTML-Post speichern ---
def save_post_as_html(text, image_url):
    #timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = output_dir / f"post_{timestamp}.html"
    html = f"""<html>
<head><meta charset="UTF-8"><title>LinkedIn Post</title></head>
<body>
<h2>LinkedIn Post Vorschau</h2>
<p>{text}</p>
<img src="{image_url}" alt="Generated Image" style="max-width:500px;">
</body></html>"""
    file_path.write_text(html, encoding="utf-8")
    return file_path



def move_to_used(file):
    # move from new to used in ../content
    return True


def list_existing_posts():
    files = list(output_dir.glob("post_*.html"))
    for i, f in enumerate(files):
        print(f"[{i}] {f.name}")
    return files