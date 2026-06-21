"""
画面上の指定範囲内でテンプレート画像を検索するプログラム
Template Matching Program for Screen Region
"""

import cv2
import numpy as np
import mss
import time
import keyboard
from PIL import Image
from datetime import datetime

# ==================== 設定 (Configuration) ====================

# 検索範囲の設定 (Search Region)
# 形式: {"top": y座標, "left": x座標, "width": 幅, "height": 高さ}
# 例: {"top": 100, "left": 100, "width": 800, "height": 600}
# 画面全体を検索する場合は、monitor=1 を使用
SEARCH_REGION = {
    "top": 700,      # 上端のY座標
    "left": 740,     # 左端のX座標
    "width": 460,    # 幅
    "height": 50    # 高さ
}

# テンプレート画像のリスト
TEMPLATES = ['01.png', '02.png', '03.png', '04.png']

# キーマッピング（テンプレート名 → 押下するキー）
KEY_MAPPING = {
    '01.png': '1',
    '02.png': '2',
    '03.png': '3',
    '04.png': '4'
}

# マッチング閾値 (0.0～1.0、高いほど厳密)
THRESHOLD = 0.8

# 検索間隔（秒）
INTERVAL = 0.5

# キー押下間隔（秒）
KEY_PRESS_INTERVAL = 0.3

# デバッグモード（Trueにすると詳細情報を表示）
DEBUG = True

# ==============================================================


def capture_screen(region):
    """
    指定範囲の画面をキャプチャする
    
    Args:
        region (dict): キャプチャする範囲 {"top", "left", "width", "height"}
    
    Returns:
        numpy.ndarray: キャプチャした画像（BGR形式）
    """
    with mss.mss() as sct:
        # スクリーンショットを取得
        screenshot = sct.grab(region)
        
        # PIL Image に変換
        img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
        
        # OpenCV形式（BGR）に変換
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        
        return img_cv


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


def main():
    """
    メイン処理: 指定間隔で画面をキャプチャし、テンプレートを検索
    """
    print("=" * 60)
    print("テンプレートマッチング開始")
    print("=" * 60)
    print(f"検索範囲: {SEARCH_REGION}")
    print(f"テンプレート: {TEMPLATES}")
    print(f"マッチング閾値: {THRESHOLD}")
    print(f"検索間隔: {INTERVAL}秒")
    print("=" * 60)
    print()
    
    # テンプレート画像を事前に読み込み（グレースケール変換済み）
    templates = load_templates(TEMPLATES)
    
    print("=" * 60)
    print(f"検索を開始します... (Ctrl+C で中断)")
    print("=" * 60)
    
    start_time = datetime.now()
    iteration = 0
    
    try:
        while True:
            iteration += 1
            
            if DEBUG:
                print(f"\n[{iteration}回目] {datetime.now().strftime('%H:%M:%S')} - 検索中...")
            
            # 画面をキャプチャ
            screen = capture_screen(SEARCH_REGION)
            
            # 全テンプレートの検索結果を格納
            results = []
            found_any = False
            
            # 各テンプレートを順次チェック
            for template_path, template_img in templates.items():
                result = find_template(screen, template_img, template_path, THRESHOLD)
                results.append(result)
                
                if DEBUG and result["confidence"] > 0.5:
                    print(f"  {template_path}: 信頼度 {result['confidence']:.2%}")
                
                # 1つでも見つかったかフラグを立てる
                if result["found"]:
                    found_any = True
            
            # 1つでも見つかった場合、全結果を表示して終了
            if found_any:
                elapsed_time = (datetime.now() - start_time).total_seconds()
                
                print("\n" + "=" * 60)
                print("✓ テンプレート検索結果")
                print("=" * 60)
                
                # 見つかったテンプレートをX座標（左から右）でソート
                found_results = [r for r in results if r["found"]]
                found_results.sort(key=lambda r: r['location'][0])
                
                # 全結果を表示
                found_count = 0
                for result in results:
                    if result["found"]:
                        found_count += 1
                        abs_x = result['location'][0] + SEARCH_REGION['left']
                        abs_y = result['location'][1] + SEARCH_REGION['top']
                        print(f"✓ {result['template']}: 見つかりました")
                        print(f"   座標: X={abs_x}, Y={abs_y}")
                        print(f"   (検索範囲内の相対座標: X={result['location'][0]}, Y={result['location'][1]})")
                        print(f"   信頼度: {result['confidence']:.2%}")
                    else:
                        print(f"✗ {result['template']}: 見つかりませんでした")
                
                print("-" * 60)
                print(f"見つかったテンプレート数: {found_count}/{len(TEMPLATES)}")
                print(f"検索回数: {iteration}回")
                print(f"経過時間: {elapsed_time:.2f}秒")
                print("=" * 60)
                
                # 左から順番にキーを押下
                if found_results:
                    print("\nキー押下処理:")
                    for i, result in enumerate(found_results, 1):
                        if result['template'] in KEY_MAPPING:
                            key = KEY_MAPPING[result['template']]
                            try:
                                keyboard.press_and_release(key)
                                print(f"  {i}. {result['template']} → キー '{key}' を押下しました (X={result['location'][0]})")
                                time.sleep(KEY_PRESS_INTERVAL) # キー押下間隔
                            except Exception as e:
                                print(f"  {i}. {result['template']} → キー '{key}' の押下に失敗: {e}")
                    print("=" * 60)
                
                # プログラム終了
                return
            
            # 指定間隔待機
            time.sleep(INTERVAL)
    
    except KeyboardInterrupt:
        print("\n\n検索を中断しました")
        elapsed_time = (datetime.now() - start_time).total_seconds()
        print(f"検索回数: {iteration}回")
        print(f"経過時間: {elapsed_time:.2f}秒")
    
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
