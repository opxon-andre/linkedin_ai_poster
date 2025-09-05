import os
import configparser

from pathlib import Path

import requests
from datetime import datetime
import json
import sys
from bs4 import BeautifulSoup

sys.path.append(os.path.join(os.path.dirname(sys.path[0])))

import app.config as cfg
import app.utils as utils


timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")



def post_to_linkedin(text, image, origin=None):
    ## origin: personal post or company post -> Setting the author
    ## company post is the default

    if origin is None:
        origin = cfg.post_as

    if origin == "company":
        curn = get_company_urn()
        company_page_id = curn.rsplit(":", 1)[-1]
        author = f"urn:li:organization:{company_page_id}"
    
    if origin == "personal": 
        purn = get_person_urn()
        person_id = purn.rsplit(":", 1)[-1]
        author = f"urn:li:person:{person_id}"

    print(f"Post as {origin}", author)

    ## prepare image for linkedin
    asset_urn, upload_url = register_image_upload(author)
    
    ## upload to linkedin
    print(f"Image {image} upload as asset {asset_urn}")
    upload_image_bytes(upload_url, image)

    resp, link = post_linkedin_api(text, asset_urn, author)
    return resp, link





def register_image_upload(owner):
    asset_api = "https://api.linkedin.com/v2/assets?action=registerUpload"
    headers = {"Authorization": f"Bearer {cfg.linkedin_token}", "X-Restli-Protocol-Version": "2.0.0"}
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
    





def get_image_path(file):
    path, file = os.path.split(file)
    file_path = f"{os.getcwd()}/content/images/{file}"
    print("Imagefile: ", file_path)
    return file_path




def upload_image_bytes(upload_url, image_path):
    file_path = get_image_path(image_path)


    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        exit()

    with open(file_path, 'rb') as f:
        headers = {
            "Authorization": f"Bearer {cfg.linkedin_token}"
        }
        response = requests.put(upload_url, headers=headers, data=f)

        # Check the response
        print(f"Image {file_path} uploaded to:{upload_url}   - with code: {response.status_code}")
        print(response.text)





# --- LinkedIn Posting ---
def post_linkedin_api(text, asset_urn, author):
    print("Poste Inhalt auf linkedIn!")
    """Post in LinkedIn hochladen"""
    api_url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {"Authorization": f"Bearer {cfg.linkedin_token}", "X-Restli-Protocol-Version": "2.0.0"}

    payload = {
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
                            "text": f"{cfg.alt_image}"
                        },
                        "media": f"{asset_urn}",
                        "title": {
                            "text": f"{cfg.alt_image}"
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
        data = json.loads(r.text)
        urn = data["id"]
        id = urn.split(":")[-1]
        company_urn = get_company_urn()
        #link = f"https://www.linkedin.com/feed/update/urn:li:activity:{id}"
        link = f"https://www.linkedin.com/company/{company_urn}/admin/dashboard/"
        print(f"Link zum neuen Post: \n{link}")
    
    return r.status_code, link




def web_post_existing_html(file):
    print(f"Web interaction: posting now file {file}")
    try:
        resp, link = post_existing_html(file)
        return resp, link
    except Exception as e:
        print("Error during posting of existing html file: ", e)
        return False, None




def get_posting_data(file_path):
    """ 
    read the file and returns all information as one dict
    Expects a full qualified path to the file
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    

    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

        content_dict = {}

        # Creation time
        c_time = ""
        c_time = soup.select_one(".timestamp").get_text(strip=True)
        content_dict.update({"c_time":c_time})

        # Confirmed-Flag auslesen
        confirmed = "No"
        confirmed_span = soup.find("span", {"class": "confirmed"})
        confirmed = confirmed_span.text.strip()
        content_dict.update({"confirmed":confirmed})

        # origin auslesen -> wird zu author
        origin = cfg.post_as
        origin_span = soup.find("span", {"class": "origin"})
        origin = origin_span.text.strip()
        content_dict.update({"origin":origin})

        # Text lesen
        text = ""
        text_span = soup.find("div", {"class": "post-text"})
        text = text_span.text.strip()
        content_dict.update({"text":text})

        # image finden
        image = ""
        img_span = soup.find("img", {"class": "post-image"})
        image = img_span.get("src")
        content_dict.update({"image":image})

        # hashtags lesen
        hashtags = ""
        hash_span = soup.find("div", {"class": "hashtags"})
        hastags = hash_span.text.strip()
        content_dict.update({"hastags":hashtags})

        # Post-Logs (Liste von dicts mit platform & timestamp)
        logs = []
        meta_section = soup.find("section", {"class": "posting-meta"})
        if meta_section:
            for log in meta_section.find_all("div", {"class": "post-log"}):
                platform = log.find("span", {"class": "platform"}).get_text(strip=True) if log.find("span", {"class": "platform"}) else None
                timestamp = log.find("span", {"class": "timestamp"}).get_text(strip=True) if log.find("span", {"class": "timestamp"}) else None
                logs.append({"platform": platform, "timestamp": timestamp})
        content_dict.update({"logs":logs})


        # Schedules lesen
        schedules = utils.get_schedules_from_post(file_path)
        content_dict.update({"schedules":schedules})

        return content_dict






# --- Einen vorhandenen HTML-Post posten ---
def post_existing_html(file_path):
    data = get_posting_data(file_path)

    origin = data["origin"]
    text = data["text"]
    confirmed = data["confirmed"]
    img_url = data["image"]

    if confirmed != "Yes":
        print("This post is not confirmed as of now! \nCannot post before.")
        return 500, None
    else:
        print("Origin: ",origin)
        resp, link = post_to_linkedin(text, img_url, origin)
        print ("Response from post_existing_html: ", resp)
        print (f"link to the new post: {link}")

        platform = "linkedin"
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
        add_post_log(file_path, platform, timestamp)

        #utils.move_to_used(file_path)
        #utils.move_to_used(img_url)

        return resp, link





def add_post_log(file_path, platform, timestamp):
    """
    Fügt in das Post-HTML einen neuen <div class="post-log">-Eintrag ein.
    add_post_log(file_path, platform, timestamp)
    Falls das <section class="posting-meta"> nicht existiert, wird es erzeugt.
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    from bs4 import BeautifulSoup

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")

    # Falls meta-Section fehlt → neu anlegen
    meta_section = soup.find("section", {"class": "posting-meta"})
    if not meta_section:
        meta_section = soup.new_tag("section", attrs={"class": "posting-meta", "style": "display:none;"})
        soup.body.append(meta_section)

    # Neuen Log-Eintrag erstellen
    post_log = soup.new_tag("div", attrs={"class": "post-log"})

    span_platform = soup.new_tag("span", attrs={"class": "platform"})
    span_platform.string = platform
    post_log.append(span_platform)

    span_timestamp = soup.new_tag("span", attrs={"class": "timestamp"})
    span_timestamp.string = timestamp
    post_log.append(span_timestamp)

    meta_section.append(post_log)

    # Datei zurückschreiben
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(soup))






def get_person_urn():
    url = "https://api.linkedin.com/v2/me"
    headers = {"Authorization": f"Bearer {cfg.linkedin_token}", "X-Restli-Protocol-Version": "2.0.0"}
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
    headers = {"Authorization": f"Bearer {cfg.linkedin_token}", "X-Restli-Protocol-Version": "2.0.0"}
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
    
