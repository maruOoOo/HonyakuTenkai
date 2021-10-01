//ESP32(2台目)に書き込むプログラム
//タッチセンサーに触れたこと（印を結んだこと）を検知しBluetoothキーボード入力として"h"をPCに送信
//プログラム更新日：2021/9/22

#include <BleKeyboard.h>

BleKeyboard bleKeyboard("ESP32KB"); //デバイスの名前を指定

void setup() {
  Serial.begin(115200);
  Serial.println("Starting BLE work!");
  bleKeyboard.begin();    //bluetooth起動
}

void loop() {
  if (bleKeyboard.isConnected()) {   //bluetoothが接続されているとき
    if(touchRead(T6) <= 20){     //タッチセンサーに触れたとき
      bleKeyboard.print("h");    //"h"キーを入力
      delay(5000);
    }
  } 
}
