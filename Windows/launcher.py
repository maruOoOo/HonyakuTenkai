#翻訳展開のランチャー
#メニュー表示-> プログラム呼び出しが主な役割
#プログラム更新日：2021/9/16

from multiprocessing import Process, Value
import msvcrt
import time
import sys
import subprocess
import os

#フラグを共有メモリとして宣言 5秒後自動スタートを実現させるために使用
#フラグが0の間はメニュー選択を受け付ける 5秒経過するとフラグが1になり、強制的にスタート
flag = Value('i', 0)


def select():
    #マルチプロセスとしてautostarterを呼び出し キー入力受付と並行して5秒カウントする
    p = Process(target=autostarter, args=(flag,))
    p.start()

    print("======Top Menu======")
    print("1. スタート  Start\n2. 言語設定  Language setting\n3. 終了      Quit")
    print("\n1 ～ 3 のキーを押してください  Press any of the keys 1 ~ 3 :")
    print("5秒後に自動的にスタートします  Automatically start after 5 seconds...")

    while True:
        #フラグが0のとき
        if flag.value == 0:
            if msvcrt.kbhit():
                p.terminate()
                p.join()
                kb = msvcrt.getch()
                if kb == b'1':
                    #1が押された場合
                    subprocess.run(["python","main.py"])   #main.py呼び出し
                    break
                elif kb == b'2':
                    #2が押された場合
                    subprocess.run(["python","settings.py"])
                    break
                elif kb == b'3':
                    #3が押された場合
                    print("終了します Quit ...")
                    break
                else:
                    #それ以外が押された場合
                    print("ERROR : 1～3 のキーを押してください")
                    select()
        
        #フラグが1のとき
        if flag.value == 1:
            p.join()
            subprocess.run(["python","main.py"])  #main.py呼び出し
            break
    
    #プログラム終了
    os.system("PAUSE")
    sys.exit()



def autostarter(flag):
    #5秒後に自動的にスタートさせる関数
    time.sleep(5)
    flag.value = 1  #5秒経ったらフラグを1に


if __name__ == '__main__':
    select()