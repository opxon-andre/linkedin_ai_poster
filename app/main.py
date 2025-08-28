import os
import linkedin_bot as bot
import utils




# --- Hauptablauf Content generation---
def create_and_save_post(dry_run=True):
    
    #text = generate_text_with_claude(text_prompt)
    #check = check_text_with_chatgpt(text)
    text = utils.generate_text()
    check = "OK"
    if check != "OK":
        print("Text nicht geeignet, hole Korrektur von Claude...")
        text = utils.generate_text_with_claude(f"Korrigiere diesen Text für LinkedIn: {text}")
    image_url = utils.generate_image(text)
    html_file = utils.save_post_as_html(text, image_url)
    print(f"Post als HTML gespeichert: {html_file}")
    if not dry_run:
        resp = bot.post_to_linkedin(text, image_url, utils.get_author())
        print(f"Direkt auf LinkedIn gepostet: {resp}")






if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "post_existing":
        posts = utils.list_existing_posts()
        idx = int(input("Wähle den Index des zu postenden HTML-Posts: "))
        resp = bot.post_existing_html(posts[idx])
        print("Post wurde auf LinkedIn veröffentlicht:", resp)
    else:
        create_and_save_post(utils.get_dry_run())  