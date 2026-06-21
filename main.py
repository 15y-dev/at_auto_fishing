"""
画面上の指定範囲内でテンプレート画像を検索するプログラム
Template Matching Program for Screen Region
"""

import cv2
import numpy as np
import mss
import time
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

# マッチング閾値 (0.0～1.0、高いほど厳密)
THRESHOLD = 0.8

# 検索間隔（秒）
INTERVAL = 0.5

# デバッグモード（Trueにすると詳細情報を表示）
DEBUG = True

# グレースケール変換を使用（マッチング精度向上）
USE_GRAYSCALE = True

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


def find_template(screen, template_path, threshold=0.8, use_grayscale=True):
    """
    画面内でテンプレート画像を検索する
    
    Args:
        screen (numpy.ndarray): 検索対象の画面画像
        template_path (str): テンプレート画像のパス
        threshold (float): マッチング閾値
        use_grayscale (bool): グレースケール変換を使用するか
    
    Returns:
        dict: {"found": bool, "location": (x, y), "confidence": float, "template": str}
    """
    try:
        # テンプレート画像を読み込む
        template = cv2.imread(template_path)
        
        if template is None:
            print(f"警告: テンプレート画像 '{template_path}' を読み込めませんでした")
            return {"found": False, "location": None, "confidence": 0.0, "template": template_path}
        
        # グレースケール変換（精度向上のため）
        if use_grayscale:
            screen = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
            template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        
        # テンプレートマッチングを実行
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        
        # 最大値とその位置を取得
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        # 閾値を超えているかチェック
        if max_val >= threshold:
            return {
                "found": True,
                "location": max_loc,
                "confidence": max_val,
                "template": template_path
            }
        else:
            return {
                "found": False,
                "location": max_loc,
                "confidence": max_val,
                "template": template_path
            }
    
    except Exception as e:
        print(f"エラー: テンプレートマッチング中にエラーが発生しました: {e}")
        return {"found": False, "location": None, "confidence": 0.0, "template": template_path}


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
            
            # 各テンプレートを順次チェック
            for template_path in TEMPLATES:
                result = find_template(screen, template_path, THRESHOLD, USE_GRAYSCALE)
                
                if DEBUG and result["confidence"] > 0.5:
                    print(f"  {template_path}: 信頼度 {result['confidence']:.2%}")
                
                # テンプレートが見つかった場合
                if result["found"]:
                    elapsed_time = (datetime.now() - start_time).total_seconds()
                    
                    print("\n" + "=" * 60)
                    print("✓ テンプレートが見つかりました！")
                    print("=" * 60)
                    print(f"テンプレート: {result['template']}")
                    print(f"座標: X={result['location'][0] + SEARCH_REGION['left']}, "
                          f"Y={result['location'][1] + SEARCH_REGION['top']}")
                    print(f"  (検索範囲内の相対座標: X={result['location'][0]}, Y={result['location'][1]})")
                    print(f"信頼度: {result['confidence']:.2%}")
                    print(f"検索回数: {iteration}回")
                    print(f"経過時間: {elapsed_time:.2f}秒")
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
