#言語設定を変更するプログラム
#プログラム更新日：2021/9/23

import json
from os import name

#json読み込み
#configのjsonファイル読み込み
with open("config.json") as f1:
    conf = json.load(f1)

#言語・音声一覧が保存されたjson（language_list.json）を読み込み
with open("language_list.json") as f2:
    lang_list = json.load(f2)

print("\n======言語設定=======")
#言語一覧表示
print("<Languages>")
for i in range(1, 71):
    print(str(i) + ". " + lang_list[str(i)]["name"])

#任意の言語設定を入力させる
Lnum = int(input("\nSelect your language : "))

#音声一覧表示
voices = lang_list[str(Lnum)]["voices"]
gender = lang_list[str(Lnum)]["gender"]
print("\n<Voices>")
for i in range(len(voices)):
    print(str(i+1) + ". " + voices[i] + " (" + gender[i] + ")")

#任意の音声設定を入力させる
Vnum = int(input("\nSelect your favorite voice : "))

#config書き換え
conf["target_lang"] = lang_list[str(Lnum)]["code"]
conf["voice_name"] = voices[Vnum - 1]

#config.json上書き保存
with open("config.json", "w") as f3:
    json.dump(conf, f3, indent=4)

print("\nChanges have been saved !")