## Telegram Spy Bot

Take Photo/Audio/Video from webcam by remotely controlling it using a Telegram bot.


### Installation & Usage:
1. Clone this repo.
1. Create `.env` file in the same directory and put `TOKEN=<your_bot_token>` and `ALLOWED_USERS=<list of userids>` in the file
1. Activate the virtual environment with `pipenv shell` and install dependencies with `pipenv install`.
1. _**Installing `pyaudio`:**_ Installing `pyaudio` in windows system can be complicated as it depends on system level audio libraries. In that case, delete the lock file, remove the pyaudio line from the pipfile and install prebuilt binaries from https://www.lfd.uci.edu/~gohlke/pythonlibs/.
1. Download and install the `ffmpeg` library for video processing. The `ffmpeg` executable should be available in the path
1. Available commands
    1. `/photo` - Take photo  
    2. `/audio` - Take audio  
    3. `/video` - Take video  
    4. `/videoonly` - Take video without audio  



