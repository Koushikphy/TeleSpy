## Telegram Spy Bot

Take Photo/Audio/Video from webcam by remotely controlling it using a Telegram bot.


### Installation & Usage:
1. Clone this repo.
1. Create `.env` file in the same directory and put `TOKEN=<your_bot_token>` and `ALLOWED_USERS=<list of userids>` in the file
1. Activate the virtual environment with `pipenv shell` and install dependencies with `pipenv install`. Make sure `pipenv` is installed.
1. Download and install the `ffmpeg` library for video processing. The `ffmpeg` executable should be available in the path.
2. Start the bot with `pipenv run bot`
1. Available commands
    1. `/photo` - Take photo  
    2. `/audio` - Take audio  
    3. `/video` - Take video  
1. A mega account is also needed to upload larger files and accordingly the mega account credentials need to be put in the .env file.

**NOTE:**
1. Telegram free account does not allow to share files larger than 50 MB. Thus, for larger recording, file will be uploaded to Mega server and the link will be shared
1. If different devices are used for video and audio recording, then there may be some sync issue.  
1. Current codebase uses a polling method for the bot to communicate with the telegram server, for a production level solution a webhook should be used.
1. A smaple `.env` file is also provided [env_sample](./.env_sample)

<!-- cut video with ffmpeg -->
<!-- ffmpeg -ss 00:01:00 -to 00:02:00  -i input.mp4 -c copy output.mp4 -->
