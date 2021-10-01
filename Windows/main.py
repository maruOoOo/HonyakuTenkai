#翻訳展開の本体となるプログラム
#GoogleDriveから画像ファイルのダウンロード-> OCR -> 翻訳-> 読み上げ を行う
#プログラム更新日：2021/9/29

from __future__ import print_function
from multiprocessing import Process, Value
import io
import os
import glob
import json
import pickle
import os.path
import time
import msvcrt
import sys
import azure.cognitiveservices.speech as speechsdk
from google.cloud import vision
from google.cloud import translate_v2 as translate
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ['https://www.googleapis.com/auth/drive']
FOLDER_NAME = 'ESP32-CAM'

#config読み込み
with open("config.json") as f:
    conf = json.load(f)

target_lang = conf["target_lang"]
voice_name = conf["voice_name"]

#azure text to speech（読み上げ）の設定
speech_key, service_region = conf["speech_key"], conf["service_region"]
speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
speech_config.speech_synthesis_voice_name = voice_name
speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)

#フラグを共有メモリとして宣言
#音声読み上げ中の間、フラグは1になる 1の間は印を結ぶと読み上げを停止させる
flg = Value('i', 0)


def main():
    print("\n======翻訳展開======")
    print("待機中  Waiting...")
    
    #無限ループでキー入力（印を結ぶ）を待機 ESP32のタッチセンサーはbluetoothを通してキーボード入力"h"として入力される
    while True:
        #フラグが0のとき
        if flg.value == 0:
            #キー入力を検出したとき
            if msvcrt.kbhit():
                kb = msvcrt.getch()
                #hが押されたとき-> 実行
                if kb == b'h':
                    time.sleep(3)
                    #ifの条件式でダウンロードを試行しつつファイルの有無を判定(返り値がTrueならば実行)
                    if download_image():
                        #ダウンロードされたjpgのファイル名を取得
                        imgfile = glob.glob('*.jpg')
                        img_filename = imgfile[0]

                        print("翻訳展開!!")
                        ocr_text = OCR(img_filename)  #引数を画像ファイル名としてOCR実行 抽出された文字列はocr_textに格納
                        print("\n--------- 読み取り結果  OCR result ---------\n" + ocr_text +  "\n--------------------------------------------\n")

                        result_text = translate_text(target_lang, ocr_text)  #翻訳 翻訳後の文字列はresult_textに格納

                        #翻訳結果に現れる余計な特殊文字を削除
                        result_text = result_text.replace("&lt;", " ")
                        result_text = result_text.replace("&quot", " ")

                        print("------- 翻訳結果  Translation result -------\n" + result_text + "\n--------------------------------------------\n")
                        
                        #マルチプロセスで読み上げの関数speechを呼び出し
                        #マルチプロセスにしているのは読み上げ中もwhileループを継続させてキー入力の受付・読み上げ強制停止を可能とするため
                        p = Process(target=speech, args=(result_text, flg))
                        p.start()

                        for i in imgfile:
                            os.remove(i)  #ダウンロードしたjpgファイルを削除

                #3が押されたとき-> プログラム終了
                if kb == b'3':
                    print("プログラム終了  Quit...")
                    sys.exit()
        
        #フラグが1のとき
        if flg.value == 1:
            #もう一度hが押されたとき-> 読み上げ停止
            if msvcrt.kbhit():
                kb = msvcrt.getch()
                if kb == b'h':
                    print("読み上げ停止 Stopped speech")
                    p.terminate()
                    flg.value = 0 #フラグを0に戻す


def OCR(img_filename):
    #インスタンス作成
    client = vision.ImageAnnotatorClient()

    #jpgファイル読み込み
    file_name = os.path.abspath(img_filename)
    with io.open(file_name, 'rb') as image_file:
        content = image_file.read()

    #OCR実行 
    image = vision.Image(content=content)

    #画像のラベル検出
    response =  client.document_text_detection(image=image)

    #文字列を抽出
    output_text = response.full_text_annotation.text
    return output_text  #文字列を返す


def translate_text(target, text):
    #文字列を翻訳する関数
    
    #翻訳 翻訳した文字列はoutputに格納
    translate_client = translate.Client()
    output = translate_client.translate(text, target_language=target)

    return output["translatedText"]   #翻訳した文字列を返す


def download_image():
    #ESP32がGoogle driveにアップロードしたjpgをダウンロードする関数

    drive = None
    creds = None

    #認証情報(OAuth)をpickleから読み込み
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        #client_secret.json(google cloudのプロジェクト、クライアントの情報などが保存されたjson)を読み込む
        elif os.path.exists('client_secret.json'):
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        #pickleが存在しない場合、ブラウザが開きログイン-> pickleに認証情報が保存される
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    if creds and creds.valid:
        drive = build('drive', 'v3', credentials=creds)
    if not drive: print('Drive auth failed.')

    #google driveのフォルダのリストを取得
    folders = None
    if drive: 
        results = drive.files().list(
            pageSize=100, 
            fields='nextPageToken, files(id, name)',
            q='name="' + FOLDER_NAME + '" and mimeType="application/vnd.google-apps.folder"'
            ).execute()
        folders = results.get('files', [])
        if not folders:
            print('No folders found.')
            return False    #google drive上にフォルダが見つからない場合Falseを返す

    #ファイルのリストを取得
    files = None
    if folders:
        query = ''
        for folder in folders:
            if query != '' : query += ' or '
            query += '"' + folder['id'] + '" in parents'
        query = '(' + query + ')'
        query += ' and (name contains ".jpg" or name contains ".png")'

        results = drive.files().list(
            pageSize=100, 
            fields='nextPageToken, files(id, name)',
            q=query
            ).execute()
        files = results.get('files', [])
        if not files:
            print('No files found on Google Drive.')
            return False     #google drive上にjpgファイルが見つからない場合Falseを返す


    #jpgダウンロード
    if files:
        for file in files:
            request = drive.files().get_media(fileId=file['id'])
            fh = io.FileIO(file['name'], mode='wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        
        #google drive上のjpgファイルを削除
        for file in files:
            drive.files().delete(fileId=file['id']).execute()

        return True  #jpgファイルが見つかった場合Trueを返す


#マルチプロセスで呼び出し
def speech(text, flg):
    #読み上げ中はフラグを1にする
    flg.value = 1
    
    #読み上げ
    result = speech_synthesizer.speak_text_async(text).get()

    #正常に読み上げられたかチェック
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print("読み上げ成功  Successful speech")
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print("Speech synthesis canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            if cancellation_details.error_details:
                print("Error details: {}".format(cancellation_details.error_details))
        print("Did you update the subscription info?")
    
    flg.value = 0   #フラグを0に戻す


if __name__ == '__main__':
    main()
