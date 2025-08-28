import os
import configparser

from pathlib import Path

import requests
import datetime

import utils


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




timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")





def post_to_linkedin(text, image, origin):
    ## origin: personal post or company post -> Seeting the author
    ## company post is the default
    
    author = f"urn:li:organization:{company_page_id}"
    if origin == "company":
        author = f"urn:li:organization:{company_page_id}"
    
    if origin == "personal": 
        author = f"urn:li:person:{person_id}"

    print(f"Poste als ", author)

    ## prepare image for linkedin
    asset_urn, upload_url = register_image_upload(author)
    
    ## upload to linkedin
    print(f"Image {image} upload as asset {asset_urn}")
    upload_image_bytes(upload_url, image)

    personal_post_to_linkedin(text, asset_urn, author)





def register_image_upload(owner):
    asset_api = "https://api.linkedin.com/v2/assets?action=registerUpload"
    headers = {"Authorization": f"Bearer {linkedin_token}", "X-Restli-Protocol-Version": "2.0.0"}
    payload = {
                "registerUploadRequest": {
                    "recipes": [
                        "urn:li:digitalmediaRecipe:feedshare-image"
                    ],
                    #"owner": f"urn:li:person:{person_id}",
                    "owner": f"{owner}",
                    "serviceRelationships": [
                        {
                            "relationshipType": "OWNER",
                            "identifier": "urn:li:userGeneratedContent"
                        }
                    ]
                }
            }
    r = requests.post(asset_api, headers=headers, json=payload)
    r.raise_for_status()
    j = r.json()
    return j["value"]["asset"], j["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
    



def upload_image_bytes(upload_url, image):
     with open(image, 'rb') as f:
        headers = {
            "Authorization": f"Bearer {linkedin_token}"
        }
        response = requests.put(upload_url, headers=headers, data=f)

        # Check the response
        print(f"Image {image} uploaded to:{upload_url}   - with code: {response.status_code}")
        print(response.text)



# --- LinkedIn Posting ---
def personal_post_to_linkedin(text, asset_urn, author):
    print("Poste Inhalt auf linkedIn!")
    """Post in LinkedIn hochladen"""
    api_url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {"Authorization": f"Bearer {linkedin_token}", "X-Restli-Protocol-Version": "2.0.0"}

    payload = {
        #"author": f"urn:li:person:{person_id}",
        "author": f"{author}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "IMAGE",
                "media": [
                    {
                        "status": "READY",
                        "description": {
                            "text": "ITSM by opXon GmbH"
                        },
                        "media": f"{asset_urn}",
                        "title": {
                            "text": "ITSM by opXon GmbH"
                        }
                    }
                ]
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    #print(payload)
    r = requests.post(url=api_url, headers=headers, json=payload)
    print("LinkedIn Response:", r.status_code, r.text)
    if r.status_code <= 300:
        data = r.text.json
        id = data.get[id]
        print(f"Link zum neuen Post: \nhttps://www.linkedin.com/feed/update/{id}")







# --- Einen vorhandenen HTML-Post posten ---
def post_existing_html(file_path):
    html_content = Path(file_path).read_text(encoding="utf-8")
    # Extrahiere Text und Bild-URL rudimentär (hier einfach via Split; für komplexere Templates BeautifulSoup nutzen)
    text_start = html_content.find("<p>") + 3
    text_end = html_content.find("</p>")
    text = html_content[text_start:text_end].strip()

    img_start = html_content.find('<img src="') + 10
    img_end = html_content.find('"', img_start)
    img_url = html_content[img_start:img_end]

    origin = "company" ## set as default
    author_start = html_content.find('<meta origin="') + 10
    author_end = html_content.find('"', author_start)
    origin = html_content[author_start:author_end]

    post_to_linkedin(text, img_url, origin)

    utils.move_to_used(file_path)
    utils.move_to_used(img_url)

    return True






def get_person_urn():
    url = "https://api.linkedin.com/v2/me"
    headers = {"Authorization": f"Bearer {linkedin_token}", "X-Restli-Protocol-Version": "2.0.0"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        person_urn = data.get("id")
        #print("LinkedIn Person URN:", person_urn)
        return f"urn:li:person:{person_urn}"
    else:
        print("Fehler:", response.status_code, response.text)
        return None
    






def get_company_urn():
    url = "https://api.linkedin.com/v2/organizationalEntityAcls?q=roleAssignee&role=ADMINISTRATOR"
    headers = {"Authorization": f"Bearer {linkedin_token}", "X-Restli-Protocol-Version": "2.0.0"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        #urn = data.get("organizationalTarget")
        urn = data['elements'][0]['organizationalTarget']
        #print("LinkedIn Company URN:", urn)
        return f"{urn}"
    else:
        print("Fehler:", response.status_code, response.text)
        return None
    
