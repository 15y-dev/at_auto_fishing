"""
画面上の指定範囲内でテンプレート画像を検索するプログラム
Template Matching Program for Screen Region
"""

import os
import cv2
import numpy as np
import mss
import time
import ctypes
import sys
import vgamepad as vg
import win32gui
import win32process
import win32api
import win32con
from ctypes import wintypes
from datetime import datetime

# ==================== 設定 (Configuration) ====================

# キャプチャ対象プログラムの実行ファイル名（プロセス名）
# 指定したプロセスのウィンドウ左上（クライアント領域）を原点(0,0)とした
# 相対座標で以下の検索範囲を指定する
TARGET_PROCESS_NAME = "game.bin"

# 検索範囲の設定 (Search Regions)
# ここで指定する座標・サイズは、TARGET_PROCESS_NAME のウィンドウ左上からの
# 相対座標（クライアント座標）である点に注意
# top / width / height は全範囲共通のため配列の外で定義
REGION_TOP = 605       # 上端のY座標（対象ウィンドウ左上からの相対値・共通）
REGION_WIDTH = 50      # 幅（共通）
REGION_HEIGHT = 50     # 高さ（共通）

# left のみ範囲ごとに異なる（左から順に登録すること・対象ウィンドウ左上からの相対値）
SEARCH_REGIONS_LEFT = [
    330,  # 範囲1
    430,  # 範囲2
    530,  # 範囲3
    620,  # 範囲4
    715,  # 範囲5
    805,  # 範囲6
    900,  # 範囲7
]

# 各範囲の完全な辞書を生成（相対座標のまま保持）
SEARCH_REGIONS_RELATIVE = [
    {"top": REGION_TOP, "left": left, "width": REGION_WIDTH, "height": REGION_HEIGHT}
    for left in SEARCH_REGIONS_LEFT
]

# テンプレート画像のリスト
TEMPLATES = ['01.png', '02.png', '03.png', '04.png']

# ボタンマッピング（テンプレート名 → Xboxコントローラーボタン）
BUTTON_MAPPING = {
    '01.png': vg.XUSB_BUTTON.XUSB_GAMEPAD_X,              # ボタン3
    '02.png': vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,              # ボタン4
    '03.png': vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,  # ボタン5 (LB)
    '04.png': vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER  # ボタン6 (RB)
}

# ボタン名マッピング（表示用）
BUTTON_NAMES = {
    vg.XUSB_BUTTON.XUSB_GAMEPAD_X: "ボタン3(X)",
    vg.XUSB_BUTTON.XUSB_GAMEPAD_Y: "ボタン4(Y)",
    vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER: "ボタン5(LB)",
    vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER: "ボタン6(RB)"
}

# マッチング閾値 (0.0～1.0、高いほど厳密)
THRESHOLD = 0.8

# 検索間隔（秒）
INTERVAL = 1.0

# ボタン押下間隔（秒）
BUTTON_PRESS_INTERVAL = 0.1


# デバッグモード（Trueにすると詳細情報を表示）
DEBUG = False

# ==============================================================

# mssインスタンスはプログラム実行時に1回だけ生成し、グローバル変数で保持する
# （毎フレーム生成すると生成コストがかかるため）
_sct = None


def capture_screen(region):
    """
    指定範囲の画面をキャプチャする
    Args:
        region (dict): キャプチャする範囲 {"top", "left", "width", "height"}
    Returns:
        numpy.ndarray: キャプチャした画像（BGR形式）
    """
    # グローバルで保持しているmssインスタンスを再利用（毎回の生成コストを削減）
    screenshot = _sct.grab(region)

    # mssはBGRA形式でバッファを返すため、PIL変換を挟まずBGRを直接取り出す
    img_bgra = np.array(screenshot)
    img_cv = img_bgra[:, :, :3]

    return img_cv


def calculate_capture_region(regions):
    """
    複数の検索範囲を全て含む、最小のキャプチャ範囲を計算する
    
    Args:
        regions (list): 検索範囲のリスト [{"top", "left", "width", "height"}, ...]
    
    Returns:
        dict: 全範囲を包含するキャプチャ範囲 {"top", "left", "width", "height"}
    """
    left = min(r['left'] for r in regions)
    top = min(r['top'] for r in regions)
    right = max(r['left'] + r['width'] for r in regions)
    bottom = max(r['top'] + r['height'] for r in regions)
    return {
        "left": left,
        "top": top,
        "width": right - left,
        "height": bottom - top
    }


def crop_region(screen, capture_region, region):
    """
    大元のキャプチャ画像から、指定範囲を切り出す
    
    Args:
        screen (numpy.ndarray): capture_regionでキャプチャした画像
        capture_region (dict): screenのキャプチャ範囲
        region (dict): 切り出したい範囲（絶対座標）
    
    Returns:
        numpy.ndarray: 切り出した画像
    """
    rel_left = region['left'] - capture_region['left']
    rel_top = region['top'] - capture_region['top']
    return screen[rel_top:rel_top + region['height'], rel_left:rel_left + region['width']]


def find_template(screen, template, template_name, threshold=0.8):
    """
    画面内でテンプレート画像を検索する
    
    Args:
        screen (numpy.ndarray): 検索対象の画面画像
        template (numpy.ndarray): テンプレート画像データ（事前読み込み済み、グレースケール）
        template_name (str): テンプレート画像の名前
        threshold (float): マッチング閾値
    
    Returns:
        dict: {"found": bool, "location": (x, y), "confidence": float, "template": str}
    """
    try:
        if template is None:
            print(f"警告: テンプレート画像 '{template_name}' が無効です")
            return {"found": False, "location": None, "confidence": 0.0, "template": template_name}
        
        # グレースケール変換（精度向上のため）
        screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        
        # テンプレートマッチングを実行
        result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        
        # 最大値とその位置を取得
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        # 閾値を超えているかチェック
        if max_val >= threshold:
            return {
                "found": True,
                "location": max_loc,
                "confidence": max_val,
                "template": template_name
            }
        else:
            return {
                "found": False,
                "location": max_loc,
                "confidence": max_val,
                "template": template_name
            }
    
    except Exception as e:
        print(f"エラー: テンプレートマッチング中にエラーが発生しました: {e}")
        return {"found": False, "location": None, "confidence": 0.0, "template": template_name}


def load_templates(template_paths):
    """
    テンプレート画像を事前に読み込む（グレースケール変換済み）
    
    Args:
        template_paths (list): テンプレート画像のパスリスト
    
    Returns:
        dict: {テンプレート名: 画像データ(グレースケール)} の辞書
    """
    templates = {}
    print("テンプレート画像を読み込み中...")
    
    for path in template_paths:
        img = cv2.imread(path)
        
        if img is None:
            print(f"  ✗ {path}: 読み込み失敗")
            templates[path] = None
        else:
            # グレースケール変換を事前に実施
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            templates[path] = img
            print(f"  ✓ {path}: 読み込み完了 ({img.shape})")
    
    print(f"読み込み完了: {len([t for t in templates.values() if t is not None])}/{len(template_paths)}個\n")
    return templates


def press_button(gamepad, button):
    """
    仮想ゲームコントローラーのボタンを押下
    
    Args:
        gamepad: vgamepadのゲームパッドオブジェクト
        button: 押下するボタン
    """
    gamepad.press_button(button=button)
    gamepad.update()
    time.sleep(0.05)
    gamepad.release_button(button=button)
    gamepad.update()


def tprint(message):
    """
    タイムスタンプ付きでprint
    
    Args:
        message (str): 表示するメッセージ
    """
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]  # ミリ秒まで表示
    print(f"[{timestamp}] {message}")


def is_admin():
    """
    管理者権限で実行されているかチェック
    
    Returns:
        bool: 管理者権限で実行されている場合True
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


class _FoundWindow(Exception):
    """
    EnumWindows のコールバック内から列挙を早期終了させるための内部例外
    """
    def __init__(self, hwnd):
        super().__init__()
        self.hwnd = hwnd


def find_hwnd_by_process_name(process_name):
    """
    指定した実行ファイル名（プロセス名）を持つプロセスの
    可視ウィンドウのハンドル(HWND)を検索する
    
    Args:
        process_name (str): 実行ファイル名 (例: "game.bin")
    
    Returns:
        int または None: 見つかったウィンドウハンドル。見つからない場合はNone
    """
    def callback(hwnd, _):
        # 非表示ウィンドウ・タイトル無しウィンドウは対象外
        if not win32gui.IsWindowVisible(hwnd):
            return True
        if not win32gui.GetWindowText(hwnd):
            return True

        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            h_process = win32api.OpenProcess(
                win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ,
                False, pid
            )
            exe_path = win32process.GetModuleFileNameEx(h_process, 0)
            win32api.CloseHandle(h_process)
        except Exception:
            # アクセス権が無い等で取得できないウィンドウは無視して続行
            return True

        if os.path.basename(exe_path).lower() == process_name.lower():
            raise _FoundWindow(hwnd)
        return True

    try:
        win32gui.EnumWindows(callback, None)
    except _FoundWindow as found:
        return found.hwnd

    return None


def get_window_client_origin(hwnd):
    """
    指定ウィンドウのクライアント領域左上を、スクリーン座標に変換して取得する
    
    Args:
        hwnd (int): ウィンドウハンドル
    
    Returns:
        tuple: (screen_x, screen_y)
    """
    return win32gui.ClientToScreen(hwnd, (0, 0))


def resolve_absolute_regions(regions_relative, origin):
    """
    対象ウィンドウ左上からの相対座標で定義された検索範囲を、
    現在のウィンドウ位置に基づく画面上の絶対座標に変換する
    
    Args:
        regions_relative (list): 相対座標の検索範囲リスト
        origin (tuple): 対象ウィンドウのクライアント領域左上のスクリーン座標 (x, y)
    
    Returns:
        list: 絶対座標に変換された検索範囲リスト
    """
    origin_x, origin_y = origin
    return [
        {
            "top": origin_y + r["top"],
            "left": origin_x + r["left"],
            "width": r["width"],
            "height": r["height"],
        }
        for r in regions_relative
    ]


def main():
    """
    メイン処理: 指定間隔で画面をキャプチャし、テンプレートを検索
    """
    global _sct

    tprint("=" * 60)
    tprint("テンプレートマッチング開始")
    tprint("=" * 60)

    # mssインスタンスをプログラム実行時に1回だけ生成（毎フレームの生成コストを削減）
    _sct = mss.mss()
    
    # 管理者権限チェック
    if is_admin():
        tprint("✓ 管理者権限で実行中")
    else:
        tprint("⚠ 警告: 管理者権限で実行されていません")
        tprint("  キー入力が正常に動作しない可能性があります")
        tprint("  run_admin.bat を使用して起動してください")

    # 対象プログラムのウィンドウを検索
    tprint(f"対象プログラム '{TARGET_PROCESS_NAME}' のウィンドウを検索中...")
    hwnd = find_hwnd_by_process_name(TARGET_PROCESS_NAME)
    if hwnd is None:
        tprint(f"エラー: プロセス '{TARGET_PROCESS_NAME}' のウィンドウが見つかりませんでした")
        tprint("  対象プログラムが起動しているか確認してください")
        return
    tprint(f"✓ ウィンドウを検出しました (HWND: {hwnd})")
    
    tprint("=" * 60)
    tprint(f"対象プロセス: {TARGET_PROCESS_NAME}")
    tprint(f"検索範囲数: {len(SEARCH_REGIONS_RELATIVE)}")
    tprint(f"テンプレート: {TEMPLATES}")
    tprint(f"マッチング閾値: {THRESHOLD}")
    tprint(f"検索間隔: {INTERVAL}秒")
    tprint("=" * 60)
    tprint("")
    
    # テンプレート画像を事前に読み込み（グレースケール変換済み）
    templates = load_templates(TEMPLATES)
    
    # 仮想Xboxコントローラーを作成
    try:
        gamepad = vg.VX360Gamepad()
        tprint("仮想Xboxコントローラーを作成しました")
    except Exception as e:
        tprint(f"エラー: 仮想コントローラーの作成に失敗: {e}")
        return
    
    tprint("=" * 60)
    tprint(f"検索を開始します... (Ctrl+C で中断)")
    tprint("=" * 60)
    
    start_time = datetime.now()
    iteration = 0
    
    try:
        while True:
            iteration += 1
            
            if DEBUG:
                tprint(f"\n[{iteration}回目] - 検索中...")

            # 対象ウィンドウがまだ存在するか確認
            if not win32gui.IsWindow(hwnd):
                tprint("⚠ 対象ウィンドウが見つからなくなりました。再検索します...")
                hwnd = find_hwnd_by_process_name(TARGET_PROCESS_NAME)
                if hwnd is None:
                    tprint(f"⚠ プロセス '{TARGET_PROCESS_NAME}' が見つかりません（スキップして継続）")
                    time.sleep(INTERVAL)
                    continue

            # ウィンドウ左上（クライアント領域）のスクリーン座標を取得し、
            # 相対座標の検索範囲を絶対座標に変換する（ウィンドウ移動に追従）
            try:
                origin = get_window_client_origin(hwnd)
                search_regions = resolve_absolute_regions(SEARCH_REGIONS_RELATIVE, origin)
                capture_region = calculate_capture_region(search_regions)
            except Exception as e:
                tprint(f"⚠ ウィンドウ座標の取得に失敗しました（スキップして継続）: {e}")
                time.sleep(INTERVAL)
                continue
            
            # 大元のキャプチャは1回だけ（一時的な失敗はスキップして継続）
            try:
                screen = capture_screen(capture_region)
            except Exception as e:
                tprint(f"⚠ 画面キャプチャに失敗しました（スキップして継続）: {e}")
                time.sleep(INTERVAL)
                continue
            
            # 各範囲を登録順（左から右）に処理
            for region_index, region in enumerate(search_regions, 1):

                # この範囲を切り出す
                sub_screen = crop_region(screen, capture_region, region)
                
                # 各テンプレートを順次チェック
                for template_path, template_img in templates.items():
                    result = find_template(sub_screen, template_img, template_path, THRESHOLD)
                    
                    if DEBUG and result["confidence"] > 0.5:
                        tprint(f"  範囲{region_index} {template_path}: 信頼度 {result['confidence']:.2%}")
                        # デバッグ用: 信頼度が閾値を超えた場合のみ切り出し画像を保存
                        cv2.imwrite(f"debug_region_{region_index}_{iteration}.png", sub_screen)
                    
                    if result["found"]:
                        # 見つかったらすぐにボタン押下
                        if template_path in BUTTON_MAPPING:
                            button = BUTTON_MAPPING[template_path]
                            button_name = BUTTON_NAMES.get(button, "不明")
                            abs_x = result['location'][0] + region['left']
                            abs_y = result['location'][1] + region['top']
                            try:
                                press_button(gamepad, button)
                                tprint(f"範囲{region_index}: {template_path} → {button_name} を押下しました "
                                       f"(座標: X={abs_x}, Y={abs_y}, 信頼度: {result['confidence']:.2%})")
                                time.sleep(BUTTON_PRESS_INTERVAL)  # ボタン押下間隔
                            except Exception as e:
                                tprint(f"範囲{region_index}: {template_path} → {button_name} の押下に失敗: {e}")
                        # この範囲では1つ見つかったら次の範囲へ
                        break
            
            # 指定間隔待機
            time.sleep(INTERVAL)
    
    except KeyboardInterrupt:
        tprint("\n\n検索を中断しました")
        elapsed_time = (datetime.now() - start_time).total_seconds()
        tprint(f"検索回数: {iteration}回")
        tprint(f"経過時間: {elapsed_time:.2f}秒")
    
    except Exception as e:
        tprint(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
