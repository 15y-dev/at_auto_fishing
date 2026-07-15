"""
スマホなどのブラウザからアクセスして、仮想Xboxコントローラーの
ボタンを押下できるようにするWebサーバー
Web Gamepad Server: Press virtual Xbox controller button from a browser (same LAN)
"""

import ctypes
import socket
import time

import vgamepad as vg
from flask import Flask, jsonify

# ==================== 設定 (Configuration) ====================

# Webサーバーの待ち受けポート
PORT = 5000

# 押下するボタン（main.py の BUTTON_MAPPING を参考）
TARGET_BUTTON = vg.XUSB_BUTTON.XUSB_GAMEPAD_X
TARGET_BUTTON_NAME = "Xボタン"

# ==============================================================


app = Flask(__name__)

# 仮想Xboxコントローラー（起動時に1度だけ生成）
gamepad = None


def is_admin():
    """
    管理者権限で実行されているかチェック

    Returns:
        bool: 管理者権限で実行されている場合True
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def get_local_ip():
    """
    同一LAN内から接続するためのローカルIPアドレスを取得する

    Returns:
        str: ローカルIPアドレス（取得失敗時は "127.0.0.1"）
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # 実際に接続はせず、ルーティング決定用に外部アドレスを指定
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def press_button(pad, button):
    """
    仮想ゲームコントローラーのボタンを押下（main.py と同じ処理）

    Args:
        pad: vgamepadのゲームパッドオブジェクト
        button: 押下するボタン
    """
    pad.press_button(button=button)
    pad.update()
    time.sleep(0.05)
    pad.release_button(button=button)
    pad.update()


# ==================== HTMLページ ====================

INDEX_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>ゲームコントローラー操作</title>
<style>
  html, body {
    margin: 0;
    padding: 0;
    height: 100%;
    background-color: #1e1e1e;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    -webkit-tap-highlight-color: transparent;
    overscroll-behavior: none;
  }
  #btn {
    width: 70vw;
    height: 70vw;
    max-width: 320px;
    max-height: 320px;
    border-radius: 50%;
    background: radial-gradient(circle at 30% 30%, #4caf50, #2e7d32);
    color: white;
    font-size: 8vw;
    font-weight: bold;
    border: none;
    box-shadow: 0 6px 12px rgba(0,0,0,0.5);
    user-select: none;
    touch-action: manipulation;
  }
  #btn:active {
    transform: scale(0.95);
    background: radial-gradient(circle at 30% 30%, #66bb6a, #1b5e20);
  }
  #status {
    position: fixed;
    bottom: 20px;
    left: 0;
    right: 0;
    text-align: center;
    color: #aaaaaa;
    font-size: 14px;
  }
</style>
</head>
<body>
  <button id="btn">X</button>
  <div id="status">準備完了</div>

<script>
const btn = document.getElementById('btn');
const status = document.getElementById('status');

function sendPress() {
  status.textContent = '送信中...';
  fetch('/press', { method: 'POST' })
    .then(res => res.json())
    .then(data => {
      if (data.ok) {
        status.textContent = data.message + ' (' + new Date().toLocaleTimeString() + ')';
      } else {
        status.textContent = 'エラー: ' + data.message;
      }
    })
    .catch(err => {
      status.textContent = '通信エラー: ' + err;
    });
}

// タップ操作（クリックの遅延・二重発火を避けるため touchstart を優先）
let touched = false;
btn.addEventListener('touchstart', function (e) {
  e.preventDefault();
  touched = true;
  sendPress();
}, { passive: false });

btn.addEventListener('click', function () {
  if (touched) {
    // touchstart で既に送信済みなのでスキップし、フラグをリセット
    touched = false;
    return;
  }
  sendPress();
});
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return INDEX_HTML


@app.route("/press", methods=["POST"])
def press():
    global gamepad
    if gamepad is None:
        return jsonify({"ok": False, "message": "コントローラーが初期化されていません"}), 500

    try:
        press_button(gamepad, TARGET_BUTTON)
        print(f"[Web] {TARGET_BUTTON_NAME} を押下しました")
        return jsonify({"ok": True, "message": f"{TARGET_BUTTON_NAME} を押下しました"})
    except Exception as e:
        print(f"[Web] ボタン押下に失敗: {e}")
        return jsonify({"ok": False, "message": str(e)}), 500


def main():
    global gamepad

    print("=" * 60)
    print("Webゲームコントローラーサーバー起動")
    print("=" * 60)

    if is_admin():
        print("✓ 管理者権限で実行中")
    else:
        print("⚠ 警告: 管理者権限で実行されていません")
        print("  ボタン入力が正常に動作しない可能性があります")
        print("  run_web_admin.bat を使用して起動してください")

    try:
        gamepad = vg.VX360Gamepad()
        print("✓ 仮想Xboxコントローラーを作成しました")
    except Exception as e:
        print(f"✗ エラー: 仮想コントローラーの作成に失敗: {e}")
        return

    local_ip = get_local_ip()
    print("=" * 60)
    print("スマホなど同一ネットワーク内の端末から、以下のURLを開いてください:")
    print(f"  http://{local_ip}:{PORT}")
    print("=" * 60)
    print("(Ctrl+C で終了)")
    print()

    app.run(host="0.0.0.0", port=PORT, debug=False)


if __name__ == "__main__":
    main()
