"""
キー入力（SendInput）が動作するか確認する

main.py の send_number() をそのまま呼び、GetAsyncKeyState で押下を検出する。
GetAsyncKeyState はフォーカスに関係なく状態を読めるため、
メモ帳を開いたりウィンドウを切り替えたりする必要はない。

使い方:
    python test_sendinput.py

対象プログラムが管理者権限で動作している場合は、こちらも管理者権限が必要
（UIPI により、低い整合性レベルのプロセスからは入力を送れないため）。
"""

import ctypes
import os

from main import send_number

VK_CODES = {"1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34}


def pressed_since_last_call(vk_code):
    """
    前回の呼び出し以降にキーが押されたかを返す。

    GetAsyncKeyState の最下位ビットは「前回この関数を呼んでから押されたか」を
    示す。押して離した後でも検出できるため、短い打鍵の確認に使える。
    """
    return bool(ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x0001)


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def main():
    print(f"セッション    : {os.environ.get('SESSIONNAME', '(不明)')}")
    print(f"管理者権限    : {'あり' if is_admin() else 'なし'}")
    print(f"INPUT構造体   : {ctypes.sizeof(__import__('main')._INPUT)} バイト (64bitでは40が正しい)")
    print("")
    print("1234 を送信して押下を検出します...")
    print("")

    detected = []

    for character in "1234":
        vk_code = VK_CODES[character]

        # 直前の状態をクリアしてから送る
        pressed_since_last_call(vk_code)

        try:
            send_number(character)
        except Exception as error:
            print(f"  '{character}' -> 送信に失敗: {error}")
            continue

        if pressed_since_last_call(vk_code):
            detected.append(character)
            print(f"  '{character}' -> 検出した")
        else:
            print(f"  '{character}' -> 検出できず")

    print("")
    print("=== 判定 ===")
    if len(detected) == 4:
        print("成功: キー入力がOSに届いています。")
        print("")
        print("あとは対象プログラムが実際に反応するかを確認してください。")
        print("OSに届いていても、Raw Input でフィルタしているプログラムには")
        print("届かない場合があります（SendInput による入力には")
        print("LLKHF_INJECTED フラグがカーネルによって自動付与されるため）。")
    elif detected:
        print(f"部分的に検出: {''.join(detected)}")
    else:
        print("検出できませんでした。管理者権限で実行しているか確認してください。")


if __name__ == "__main__":
    main()
