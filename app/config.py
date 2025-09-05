import configparser
import requests
import datetime
import base64
import os
import random
import time
import random

from datetime import datetime
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

from pathlib import Path
from openai import OpenAI


# --- Konfiguration laden ---
CONFIG_FILE = f"{os.getcwd()}/config/config.ini"
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
demo =              config["OPTIONS"]["demo"]

system_prompt =     config["PROMPTS"]["system_prompt"].strip('"').strip("'")
check_prompt =      config["PROMPTS"]["check_prompt"].strip('"').strip("'")
text_prompt_file =  config["PROMPTS"]["text_file"].strip('"').strip("'")
promptpath = Path(f"{os.getcwd()}/config/{text_prompt_file}")


# --- Prompts laden ---
prompts = configparser.ConfigParser()
prompts.read(f"{os.getcwd()}/config/prompts")

text_prompt =       prompts["PROMPTS"]["text_prompt"].strip('"').strip("'")
image_prompt =      prompts["PROMPTS"]["image_prompt"].strip('"').strip("'")






output_dir = Path(f"{os.getcwd()}/content/new")
output_dir.mkdir(exist_ok=True)

used_dir = Path(f"{os.getcwd()}/content/used")
used_dir.mkdir(exist_ok=True)



