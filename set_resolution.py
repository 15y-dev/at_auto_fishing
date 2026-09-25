"""
tscon でコンソールへ移った後に、ダミープラグの解像度を変更するスクリプト。
画面が見えない状態で動くため、結果は同じフォルダの resolution_log.txt に記録する。

必要なもの: pip install pywin32
"""
import datetime
import os
import time

import pywintypes
import win32api
import win32con

WIDTH, HEIGHT = 1920, 1200
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resolution_log.txt")


def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")


def available_modes():
    """現在のディスプレイで選択できる解像度の一覧を返す"""
    modes, i = set(), 0
    while True:
        try:
            dm = win32api.EnumDisplaySettings(None, i)
        except pywintypes.error:
            break
        modes.add((dm.PelsWidth, dm.PelsHeight))
        i += 1
    return sorted(modes)


def set_resolution(w, h):
    dm = win32api.EnumDisplaySettings(None, win32con.ENUM_CURRENT_SETTINGS)
    if (dm.PelsWidth, dm.PelsHeight) == (w, h):
        log(f"すでに {w}x{h} です")
        return True
    dm.PelsWidth, dm.PelsHeight = w, h
    dm.Fields = win32con.DM_PELSWIDTH | win32con.DM_PELSHEIGHT
    result = win32api.ChangeDisplaySettings(dm, win32con.CDS_UPDATEREGISTRY)
    if result == win32con.DISP_CHANGE_SUCCESSFUL:
        log(f"{w}x{h} に変更しました")
        return True
    log(f"変更失敗 (戻り値 {result})")
    return False


if __name__ == "__main__":
    # 切り替え直後はディスプレイが安定しないことがあるので数回リトライ
    for attempt in range(5):
        modes = available_modes()
        if (WIDTH, HEIGHT) in modes:
            if set_resolution(WIDTH, HEIGHT):
                break
        else:
            log(f"{WIDTH}x{HEIGHT} は選択肢にありません。利用可能: {modes}")
        time.sleep(2)
