# code.py — PCからUSBシリアル(データ用ポート)で受け取った数字を、
# USBキーボードのキー入力としてPCへ送信する (CircuitPython)
#
# 前提: boot.py で usb_cdc.enable(console=True, data=True) を設定済みであること
# 受信フォーマット: ASCII の数字 '0'～'9' を1文字ずつ（改行などの他の文字は無視）
import time
import board
import digitalio
import usb_cdc
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

# キーを押している時間（秒）
KEY_PRESS_DURATION = 0.05

# 数字文字 → キーコード（キーボードレイアウトに依存しないよう Keycode を直接使用）
KEY_MAP = {
    "0": Keycode.ZERO,
    "1": Keycode.ONE,
    "2": Keycode.TWO,
    "3": Keycode.THREE,
    "4": Keycode.FOUR,
    "5": Keycode.FIVE,
    "6": Keycode.SIX,
    "7": Keycode.SEVEN,
    "8": Keycode.EIGHT,
    "9": Keycode.NINE,
}

led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

keyboard = Keyboard(usb_hid.devices)
serial = usb_cdc.data

if serial is None:
    # boot.py の設定が反映されていない場合
    print("usb_cdc.data が無効です。boot.py を確認してUSBを抜き差ししてください")
    while True:
        led.value = not led.value
        time.sleep(0.1)

print("数字受信待機中 (usb_cdc.data)")

while True:
    count = serial.in_waiting
    if count:
        data = serial.read(count)
        for b in data:
            ch = chr(b)
            keycode = KEY_MAP.get(ch)
            if keycode is None:
                continue
            led.value = True  # 送信中はLED点灯
            keyboard.press(keycode)
            time.sleep(KEY_PRESS_DURATION)
            keyboard.release_all()
            led.value = False
            time.sleep(KEY_PRESS_DURATION)  # 連続入力時のキー間隔
    else:
        time.sleep(0.005)
