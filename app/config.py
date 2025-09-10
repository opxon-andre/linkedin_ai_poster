import configparser
import os
from zoneinfo import ZoneInfo
from pathlib import Path
import sys


CONFIG_FILE = f"{os.getcwd()}/config/config.ini"
if not os.path.exists(CONFIG_FILE):
    CONFIG_FILE = f"{os.getcwd()}/config/config.ini.TEMPLATE"

try:
    # --- Konfiguration laden ---
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)

    openai_token =      config["API"]["openai_token"].strip('"').strip("'")
    openai_model =      config["API"]["openai_model"].strip('"').strip("'")

    claude_api_key =    config["API"]["claude_token"].strip('"').strip("'")
    claude_model =      config["API"]["claude_model"].strip('"').strip("'")

    text_ai =           config["API"]["text_ai"].strip('"').strip("'")
    image_ai =          config["API"]["image_ai"].strip('"').strip("'")

    linkedin_token =    config["API"]["linkedin_token"].strip('"').strip("'")

    linkedin_tpl =      config["TEMPLATES"]["linkedin"].strip('"').strip("'")
    post_as =           config["TEMPLATES"]["post_as"].strip('"').strip("'")
    company_name =      config["TEMPLATES"]["company_name"].strip('"').strip("'")
    company_tagline =   config["TEMPLATES"]["tagline"].strip('"').strip("'")
    alt_image =         config["TEMPLATES"]["alt_image"]

    post_start =        config["SCHEDULER"]["post_start"].strip('"').strip("'")
    post_end =          config["SCHEDULER"]["post_end"].strip('"').strip("'")
    timezone = ZoneInfo(config["SCHEDULER"]["timezone"].strip('"').strip("'"))

    dry_run =           config["OPTIONS"]["dry_run"].strip('"').strip("'")
    #dry_run = eval(s_dry_run.lower())
    s_demo =              config["OPTIONS"]["demo"].strip('"').strip("'").lower()
    demo = False
    if s_demo == "true":
        demo = True
    #demo = eval(s_demo.lower())

    system_prompt =     config["PROMPTS"]["system_prompt"].strip('"').strip("'")
    check_prompt =      config["PROMPTS"]["check_prompt"].strip('"').strip("'")
    text_prompt_file =  config["PROMPTS"]["text_file"].strip('"').strip("'")
    promptpath = Path(f"{os.getcwd()}/config/{text_prompt_file}")

    loglevel =          config["LOGGING"]["loglevel"].strip('"').strip("'")
    logpath = f"{os.getcwd()}{config["LOGGING"]["logpath"].strip('"').strip("'")}"

except Exception as e:
    print(f"failed reading config File {CONFIG_FILE} ")



try:
    # --- Prompts laden ---
    PROMPS_FILE = f"{os.getcwd()}/config/prompts"
    prompts = configparser.ConfigParser()
    prompts.read(PROMPS_FILE)

    text_prompt =       prompts["PROMPTS"]["text_prompt"].strip('"').strip("'")
    image_prompt =      prompts["PROMPTS"]["image_prompt"].strip('"').strip("'")

except Exception as e:
    print(f"failed reading config File {PROMPS_FILE} ")





output_dir = Path(f"{os.getcwd()}/content/new")
output_dir.mkdir(parents=True, exist_ok=True)

used_dir = Path(f"{os.getcwd()}/content/used")
used_dir.mkdir(parents=True, exist_ok=True)



