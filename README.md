This is the LinkedIn AI Assisted Autoposter!

It is a simplyfied python script for those who have to post content often to LinkedIn, without the need to copy and paste from your favorite AI manualy.


Setup:
General Part
1. clone this repository to a place you like
2. rename the files 
   /config/config.ini.TEMPLATE ->  /config/config.ini
   /config/prompts.SAMPLE  -> /config/prompts
3. The parameters in config.ini are described below, so be patient!
4. Make yourself familiar how to prompt content for your target group. The Sammple is really not useful for anybody! You can try prompting with the chatgpt chatbot, and as soon you are happy with the result, take that prompt in the prompts file. 
5. Same with the prompt for image generation. Don´t overcomplicate it! Choose style you like and keep the prompt short. Otherwise you´ll get always similar output.
6. Install the python requirements: pip install -r requirements.txt 


LinkedIn Part
1. First you need to have Company Page at LinkedIn. Even you do not run a company, you cannot use the LI API without that page.
2. Then you need to apply for the LinkedIn Developers Programm:
   2.1 Go to https://developer.linkedin.com/ and login with your ususal credentials.
   2.2 Hit the "Create App" Button (beyond My Apps)
   2.3 Fill out the form including your Website URL. For the OAuth 2.0 redirect URL. use this link to your computer first: http://localhost:8080/callback
   2.4 Once you are done with these steps, you get presented a page for your fresh created App. Go to the "Auth" Page of it, and see your ClientID and Secret. Do not copy this anywhere! It is not needed in the config for the AI_Poster!
4. Get your Access Token
   3.1 Go to https://www.linkedin.com/developers/tools/oauth/token-generator?clientId=XYZ123  <- replace XYZ123 with your own ClientID
   3.2 Select your new App from the Dropdown
   3.3 Select Member Authorization Code
   3.4 Hit request Token
   3.5 write this Token into the config.ini as linkedin_token
5. Go back to your App (My Apps), to the Products Tile
   5.1 Request Access to "Share on LinkedIn", "Advertising API", and "Sign in with LinkedIn using OpenID Connect".
     Some of those require to fill out a request form. Be honest but careful with that. These forms are really checked, and LinkedIn tends to be picky to grant access.
   5.2 Now you need to wait for the approvals, and to get access to the API Endpoints. That may take a while (at least 2-3 hours, sometimes a day) 
     You can check at the Auth Tile of your App, if you have the OAuth 2.0 Scopes for: openid, r_organization_social, w_organizational_social and w_member_social.

   
If you struggle at any point, check out this page: https://www.scrapin.io/blog/linkedin-api
The Area below "Creating a LinkedIn App with a Developer Account" is really helpful 


openAI
You need to have an account at openAI and access to the API. That is usually given for (pre) paid accounts. Follow the various instructions how to get an openAI API Key.
Fill in the openAI API Key into the config.ini File


ClaudeAI
You can use claude AI if you like. But the results are not that nice as they are with openai
Follow the instructions how to get an API Key for Claude, and fill it in the config.ini. If you do not want to use claude (which is the default), keep the parameter "claude_token", but with an empty value.

   
#######################################

How to use
To generate new content without posting it ensure the config parameter dry_run is set to True. Then simply call "python ./main.py" within the app directory. this will create a new suggestion as a html file in the directory content/new. A related image will be saved in content/images.

To post that fresh content, call "python ./main.py post_existing" and follow the instructions.

With setting the dry_run parameter to false, you enter the semi auto mode. The content will be created and posted in one turn by calling "python ./main.py".



#####################################

Open Topics
- A Dockerized Version will follow soon
- The Scheduler will follow after the Docker Version. That will post content within a (already) configurable timeframe.


