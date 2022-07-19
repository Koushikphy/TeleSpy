from utils import * 
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging, shutil

TOKEN = os.getenv('TOKEN')
ALLOWED_USERS = [int(i) for i in os.getenv('ALLOWED_USERS').split()]  
ADMIN = os.getenv('ADMIN')

bot = TeleBot(TOKEN, parse_mode='HTML')



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


recorder = AVRecorder()
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
    user = message.from_user.id
    if checkRequest(message):
        return

    if recorder.isRunning:
        bot.send_message(user, "Device is busy. Can't capture photo.")
        return

    waitM = bot.send_message(user, "Wait while the bot takes the photo")
    file = recorder.takePicture()

    with open(file, 'rb') as f:
        try:
            photoM = bot.send_photo(user, f, caption="This photo will be deleted after 5 seconds.", reply_markup=photoMarkup())
        except Exception as e:
            logger.info(e)
    
    photoK.queueToDelete(message, photoM)
    bot.delete_message(waitM.chat.id, waitM.message_id)


def photoMarkup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton("Keep this photo", callback_data="cb_keep_photo"))
    return markup



class PhotoKeeper():
    # if multiple photos are present this will mess up the callback
    def __init__(self):
        self.delay = 5  # 5

    def tmpDelete(self,*messages):
        for i in messages:
            bot.delete_message(i.chat.id, i.message_id)

    def queueToDelete(self, commandM, photoM):
        self.photoM = photoM
        self.timer = Timer(self.delay, self.tmpDelete,[commandM, photoM])
        self.timer.start()
        
    def keepPhoto(self):
        self.timer.cancel()
        bot.edit_message_caption("",self.photoM.chat.id, self.photoM.message_id,reply_markup=None)


photoK = PhotoKeeper()


@bot.message_handler(commands='audio')
def send_audio(message):
    # start audio recording
    user = message.from_user.id
    if checkRequest(message):
        return

    if recorder.isRunning:
        bot.send_message(user, "Recording already in progress.")
    else:
        recorder.startAudeoRec()
        bot.send_message(user, "Recording in progress.", reply_markup=mediaMarkup())
        remind.remind(user)



@bot.message_handler(commands='video')
def send_video(message):
    user = message.from_user.id
    if checkRequest(message):
        return

    if recorder.isRunning:
        bot.send_message(user, "Recording already in progress.")
    else:
        recorder.startVideoRec()
        bot.send_message(user, "Recording in progress.", reply_markup=mediaMarkup())
        remind.remind(user)



def mediaMarkup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton("Finish", callback_data="cb_stop_recording"),
               InlineKeyboardButton("Cancel", callback_data="cb_cancel_recording"))
    return markup




@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):

    if call.data == "cb_keep_photo":
        photoK.keepPhoto()
        return

    deleteMessage(call.message)
    remind.cancel()  # clear all reminder
    user = call.from_user.id

    if not recorder.isRunning :
        bot.send_message(user, "No recording is currently in progress !!!")
        return

    if call.data == "cb_stop_recording":
        file, act = recorder.close()

        logger.info(f"Recording finished: {os.path.basename(file)} ({act:.2f} sec) ({os.path.getsize(file)/1e6:.2f} MB)")
        files = splitFilesInChunks(file)
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

        deleteMessage(message)


    elif call.data == "cb_cancel_recording":
        file,_= recorder.close()
        os.remove(file)
        bot.send_message(user, "Recording terminated")
        logger.info('Recording terminated')




bot.send_message(ADMIN, "Starting bot")
bot.infinity_polling()