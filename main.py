import cv2 # OpenCV
# Discord
from discordwebhook import Discord
import aiohttp
# import slackweb
import datetime
import copy
# 文字認識のため
import pyocr
import pyocr.builders
from PIL import Image
import re # 正規表現
import os # .env 環境変数
from dotenv import load_dotenv
load_dotenv()


# Discord Webhook URL
discord = Discord(url=os.environ['DISCORD_WEBHOOK_URL'])
# Slackだとお仕事感のある通知音になるのでやめ
# slack = slackweb.Slack(url="")

template = cv2.imread(os.environ['TEMPLATE_IMAGE_PATH']) #テンプレート画像
template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY) #グレイスケールに変換

# 画像認識したい部分の許容範囲。テンプレート画像のサイズを変えたらこちらも変える必要がある
h_min = 350; h_max = 360; w_min = 90; w_max = 115

# マッチング閾値。これを超えたら歪み認定
match_max = 0.42

log_interval = int(datetime.datetime.utcnow().timestamp())
unmatch_max_value = 0

# print(cv2.getBuildInformation())

capture = cv2.VideoCapture(1)

capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# 文字認識
pyocr.tesseract.TESSERACT_CMD = 'C:/Program Files/Tesseract-OCR/tesseract.exe'
tools = pyocr.get_available_tools()
tool = tools[0]

# テンプレートマッチング
def template_match(img,img_color):
    global log_interval, unmatch_max_value
    global h_min, h_max, w_min, w_max, match_max
    flag = False
    h, w = template.shape[0],template.shape[1]
    match = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)

    _min_value, max_value, _min_pt, max_pt = cv2.minMaxLoc(match)
    pt = max_pt
    temp_out = copy.deepcopy(img_color[pt[1]:pt[1]+h,pt[0]:pt[0]+w])
    # 指定のWIDTH, HEIGHT の範囲で指定のmax_value以下のマッチングがあれば検知とみなす
    # つまり、ゲーム画面でメッセージが表示される領域あたりに絞っているということ
    if h_min<pt[0] and pt[0]<h_max and w_min<pt[1] and pt[1]<w_max:

      print(f"area match: max value: {max_value}, position: {max_pt}, {datetime.datetime.now()}")
      if max_value > match_max: 
        # 時空の歪みを検知
        # 検知用テンプレ画像につかったりするので囲わない
        # cv2.rectangle(img_color, (pt[0], pt[1]), (pt[0] + w, pt[1] + h), (0, 200, 0), 3)
        print(f"======detect:{max_value}======")
        flag = True

      ocr_str = ocr_yugami(temp_out)
      print(f"OCR: {ocr_str[0]}")

      # 特定の文字列が含まれていれば歪みではないのでFalseに切り替える
      pattern = r'豪雨|道具|先には'
      result = re.compile(pattern)
      if bool(result.search(ocr_str[0])):
        flag = False
        print("文字列から歪みじゃないと判断")
        cv2.waitKey(2000) # 文字列からNot歪み判定した場合は誤判定を防ぐため数秒待つ

      return flag,img_color,temp_out
    else:
        # 時空の歪みを非検知
        cv2.rectangle(img_color, (pt[0], pt[1]), (pt[0] + w, pt[1] + h), (0, 0, 200), 3)
        # print(f"max value: {max_value}, position: {max_pt}")

        # 調査のためにマッチ率が過去一高いものを出力しておく
        if unmatch_max_value < max_value:
          unmatch_max_value = max_value
          print(f"max value: {max_value}, position: {max_pt}, {datetime.datetime.now()}")
          ocr_str = ocr_yugami(temp_out)
          print(f"OCR: {ocr_str[0]}")
          
        return flag,img_color,temp_out


def ocr_yugami(img):
  img = Image.fromarray(img)
  builder = pyocr.builders.TextBuilder()
  result = tool.image_to_string(img, lang="jpn", builder=builder)
  data_list = [text for text in result.split('\n') if text.strip()]
  data_list
  # print(f"OCR: {data_list}")
  if not data_list:
    data_list.append('')
  return data_list


if capture.isOpened() is False:
  raise IOError

while(True):
  try:
    ret, frame = capture.read()
    if ret == False:
      # print(f"video caputure failed. wait 1 sec and continue...")
      # cv2.waitKey(1000)
      # continue
      raise IOError

    frame_color = copy.deepcopy(frame)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) # グレイスケールに変換
    if ret is False:
      raise IOError

    flag,frame_out,temp_out = template_match(frame,frame_color)
    
    if flag: # Discordに通知
      # ocr_str = ocr_yugami(temp_out)
      cv2.imwrite("./pic/frame_out.jpg", frame_out)
      cv2.imwrite("./pic/template_out.jpg", temp_out)
      f1 = open("./pic/frame_out.jpg", 'rb')
      f2 = open("./pic/template_out.jpg", 'rb')
      dt_now = datetime.datetime.now() # 現在時刻取得
      message = "@here 時空の歪み検知 " + dt_now.strftime('%Y年%m月%d日 %H:%M:%S')
      discord.post(content=message,file={"1": f1,"2": f2})
      # slack.notify(text="@here 時空の歪み検知 " + dt_now.strftime('%Y年%m月%d日 %H:%M:%S'))
      cv2.waitKey(500) # 連投を防ぐため1秒くらいは待つ。3回位の連投に落ち着く想定

    cv2.imshow('frame',frame_out)
    cv2.waitKey(10)

  except KeyboardInterrupt:
    break

capture.release()
cv2.destroyAllWindows()

# MEMO: 誤判定した文字列リスト
# まもなく豪雨がやみそうだ
# この道具は持ちきれません
# これより先には進めません

# せいかい
# 時空の歪みが発生しそうだ