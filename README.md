# Twitch-Discord-Bot
This Discordbot will send a notification message in a given Discord-chatchannel whenever certain streamers start their stream. This is just the code for the bot and can be setup in a docker container to run in 24/7.

There will be a video/tutorial on how I set up my bot on a Raspberry Pi 4 and Docker in the near future.

----------------------------------------------------------------------------

Update:
Create new folder for the bot on your machine that will have docker run 24/7:
	mkdir -p ~/discordbot
	cd ~/discordbot
	
copy/paste three files into that folder: discordbot.py; requirements.txt; Dockerfile

requirements.txt:
	discord.py
	aiohttp
	python-dotenv

Dockerfile:
	FROM python:3.12-slim
	WORKDIR /app
	ENV PYTHONUNBUFFERED=1
	COPY requirements.txt .
	RUN pip install --no-cache-dir -r requirements.txt
	COPY discordBot.py .
	RUN useradd -botuser
	USER botuser
	CMD ["python", "-u", "discordBot.py"]
	
Build image for docker:
	cd ~/discordbot
	docker build -t discord-twitch-bot:1.0 .
	
Open Portainer and select your environment (your version of portainer)
Open Stacks -> Add stack -> stack name (e.g. discord-twitch-bot)
Edit YAML:
	services:
  bot:
    image: discord-live-bot:1.0
    container_name: discord-live-bot
    restart: unless-stopped
    environment:
      DISCORD_TOKEN: GET YOUR DISCORD TOKEN 
      DISCORD_CHANNEL_ID: GET THE CHANNEL ID 
      TWITCH_CLIENT_ID: GET YOUR TWITCH CLIENT ID
      TWITCH_CLIENT_SECRET: GET YOUR TWITCH CLIENT SECRET
      TZ: INSERT YOUR TIMEZONE
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
        
In order to find your discord_token, twitch_client_id and twitch_client_secret, you have to visit those websites:
  https://discord.com/developers/applications
  https://dev.twitch.tv/console/apps
Login with your Discord and Twitch accounts. 
On the discord website, you have to create a new application, go to OAUTH2, copy/paste the token and set OAuth2 URL Generator scopes to bot + give your bot the necessary permissions.
Afterwards copy paste the generated URL into your browser so that the bot will be invited to your discord server. Next, give your bot all the permissions that you want and find the channel
where it should post the notifications. Right click on that channel, copy the channel ID and insert it at discord_channel_id. 
For Twitch, you have to register a new application, give it a name, set the OAUTH redirect URLs to "http://localhost:3000", select the category as "Chat Bot". Below that are your client_id and
client_secret. Copy paste those into YAML on portainer.
To get your timezone, just google "What's my timezone". Google should answer that question.


To update your code, you have to build a new image and update the stack + redeploy
	docker build -t discord-twitch-bot:1.1 .
	Edit YAML -> update image -> discord-live-bot:1.0 >> discord-live-bot:1.1
	docker restart discord-twitch-bot

Everything *should* work. If you have any questions, feel free to send me a message on Discord or on Twitch. My username is "Alexmeisteer" on both platforms. 
