# 書籍貸出機能の拡張計画 (第2版)

## 概要

`main_menu.html` ウェブページの "貸出" (Lending) ボタンを押下した際に、以下の処理を実行する。

1.  `main_menu.html` ウェブページを非表示にする。
2.  Windows 実行ファイル `yorimichi_z.exe` ( `/exes` フォルダ内) を実行する。これにより、NFC リーダー (PaSoRi) のポーリングが開始される。
3.  Windows 実行ファイル `yorimichi_z2.exe` ( `/exes` フォルダ内) を実行する。これにより、従業員 ID カードを PaSoRi リーダーにタップするように促す画像が表示される。
4.  従業員 ID カードのタップが成功すると、`yorimichi_z.exe` がカードから従業員番号を読み取り、システムクリップボードにペーストする。
5.  20 秒以内にクリップボードに値がペーストされない場合、"社員証が検出されませんでした。" というメッセージを表示し、`yorimichi_z2.exe` プロセスを終了し、`main_menu.html` ウェブページを再表示する。

## 詳細な手順

1.  **`app.py` の変更:**
    *   `apply_diff` ツールを使用して、`app.py` に以下のAPIエンドポイントを追加する。

    ```python
    import subprocess
    import os
    import time
    from flask import Flask, jsonify

    app = Flask(__name__)

    @app.route('/execute_yorimichi')
    def execute_yorimichi():
        try:
            # 1. プロセスの実行
            process_z = subprocess.Popen([os.path.join("exes", "yorimichi_z.exe")], creationflags=subprocess.CREATE_NO_WINDOW)
            process_z2 = subprocess.Popen([os.path.join("exes", "yorimichi_z2.exe")], creationflags=subprocess.CREATE_NO_WINDOW)

            # 2. タイムアウト設定
            timeout = 20  # 秒

            # 3. プロセスの監視とタイムアウト処理
            start_time = time.time()
            while True:
                # プロセスの終了をポーリング
                return_code_z = process_z.poll()
                return_code_z2 = process_z2.poll()

                # いずれかのプロセスが終了した場合
                if return_code_z is not None or return_code_z2 is not None:
                    break

                # タイムアウトチェック
                elapsed_time = time.time() - start_time
                if elapsed_time > timeout:
                    print("タイムアウト: プロセスを強制終了します")
                    process_z.terminate()
                    process_z2.terminate()
                    return jsonify({'status': 'timeout', 'message': '社員証が検出されませんでした。'})

                # 短いスリープ
                time.sleep(0.1)

            # 4. プロセスの終了コードの確認
            if return_code_z == 0 and return_code_z2 == 0:
                print("プロセスは正常に終了しました")
                return jsonify({'status': 'success', 'message': 'プロセスは正常に終了しました'})
            else:
                print(f"プロセスはエラーで終了しました (終了コード: {return_code_z}, {return_code_z2})")
                return jsonify({'status': 'error', 'message': f'プロセスはエラーで終了しました (終了コード: {return_code_z}, {return_code_z2})'})

        except Exception as e:
            print(f"エラーが発生しました: {e}")
            return jsonify({'status': 'error', 'message': str(e)})

    if __name__ == '__main__':
        app.run(debug=True)
    ```

2.  **`static/js/navigation.js` の変更:**
    *   `apply_diff` ツールを使用して、`static/js/navigation.js` を変更し、APIエンドポイントを呼び出すようにする。

    ```javascript
    // --- main_menu.html 用 ---
    const lendingButton = document.getElementById('lendingButton');
    if (lendingButton) {
        lendingButton.addEventListener('click', () => {
            // 1. main_menu.html を非表示にする
            document.body.style.display = 'none';

            // 2. yorimichi_z.exe と yorimichi_z2.exe を実行する
            fetch('/execute_yorimichi')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        alert("従業員番号: " + clipboardValue); // クリップボードの値を取得する方法は別途検討
                    } else if (data.status === 'timeout') {
                        alert("社員証が検出されませんでした。");
                    } else {
                        alert("エラーが発生しました: " + data.message);
                    }
                })
                .catch(error => {
                    console.error('API呼び出しエラー:', error);
                    alert("API呼び出しエラーが発生しました。");
                })
                .finally(() => {
                    // 5. main_menu.html を再表示する
                    location.reload();
                });
        });
    } else {
        // console.log('#lendingButton button not found on this page.'); // デバッグ用
    }
    ```

3.  **`templates/main_menu.html` の変更:**
    *   `apply_diff` ツールを使用して、`templates/main_menu.html` の "貸出" (Lending) ボタンに、ID属性を追加する。

    ```html
    <button type="button" class="btn btn-large" id="lendingButton">貸出</button>
    ```

## エラー処理、ログ出力、実行環境、非同期処理に関する考慮事項

*   **エラー処理:**
    *   Python側では、`try...except` ブロックを使用して、プロセスの実行時やAPI呼び出し時のエラーをキャッチする。
    *   JavaScript側では、`fetch` APIの `catch` メソッドを使用して、API呼び出し時のエラーをキャッチする。
*   **ログ出力:**
    *   Python側では、`print` 関数を使用して、プロセスの実行状況やエラー情報をコンソールに出力する。
    *   JavaScript側では、`console.error` 関数を使用して、API呼び出し時のエラー情報をブラウザのコンソールに出力する。
*   **実行環境:**
    *   `yorimichi_z.exe` と `yorimichi_z2.exe` が `/exes` フォルダに存在することを確認してください。
    *   Pythonの `subprocess` モジュールが利用可能であることを確認してください。
*   **非同期処理:**
    *   Python側では、`subprocess.Popen` 関数を使用して、プロセスを非同期的に実行する。
    *   JavaScript側では、`fetch` APIを使用して、API呼び出しを非同期的に行う。
    *   タイムアウト処理は、Python側で `time.sleep` 関数と `process.poll` 関数を使用して実装する。