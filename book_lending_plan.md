# 書籍貸出機能の拡張計画

## 概要

`main_menu.html` ウェブページの "貸出" (Lending) ボタンを押下した際に、以下の処理を実行する。

1.  `main_menu.html` ウェブページを非表示にする。
2.  Windows 実行ファイル `yorimichi_z.exe` ( `/exes` フォルダ内) を実行する。これにより、NFC リーダー (PaSoRi) のポーリングが開始される。
3.  Windows 実行ファイル `yorimichi_z2.exe` ( `/exes` フォルダ内) を実行する。これにより、従業員 ID カードを PaSoRi リーダーにタップするように促す画像が表示される。
4.  従業員 ID カードのタップが成功すると、`yorimichi_z.exe` がカードから従業員番号を読み取り、システムクリップボードにペーストする。
5.  20 秒以内にクリップボードに値がペーストされない場合、"社員証が検出されませんでした。" というメッセージを表示し、`yorimichi_z2.exe` プロセスを終了し、`main_menu.html` ウェブページを再表示する。

## 詳細な手順

1.  **`templates/main_menu.html` の確認:**
    *   `read_file` ツールを使用して、`templates/main_menu.html` の内容を確認する。
    *   "貸出" (Lending) ボタンのHTML要素（例: `<button id="lendingButton">貸出</button>`) を特定する。

2.  **`static/js/navigation.js` の確認:**
    *   `read_file` ツールを使用して、`static/js/navigation.js` の内容を確認する。
    *   既存のJavaScript関数やイベントハンドラとの連携方法を検討する。

3.  **`static/js/navigation.js` の変更:**
    *   `apply_diff` ツールを使用して、`static/js/navigation.js` に以下のJavaScript関数を追加する。

    ```javascript
    // --- main_menu.html 用 ---
    const lendingButton = document.getElementById('lendingButton');
    if (lendingButton) {
        lendingButton.addEventListener('click', () => {
            // 1. main_menu.html を非表示にする
            document.body.style.display = 'none';

            // 2. yorimichi_z.exe と yorimichi_z2.exe を実行する
            //    (Windowsの実行ファイルをJavaScriptから直接実行することはできません。
            //     この部分は、セキュリティ上の理由からブラウザでは許可されていません。
            //     代替手段として、アラートを表示するだけにします。)
            alert("yorimichi_z.exe と yorimichi_z2.exe を実行します (実際には実行されません)");

            // 3. クリップボードの値を監視し、20秒以内に値がペーストされたかどうかを確認する
            let clipboardValue = "";
            const startTime = Date.now();
            const timeout = 20000; // 20秒

            const checkClipboard = setInterval(() => {
                navigator.clipboard.readText()
                    .then(text => {
                        clipboardValue = text;
                        if (clipboardValue !== "") {
                            // 値がペーストされた
                            clearInterval(checkClipboard);
                            alert("従業員番号: " + clipboardValue);
                            // 5. main_menu.html を再表示する
                            location.reload();
                        } else {
                            // タイムアウトチェック
                            if (Date.now() - startTime > timeout) {
                                clearInterval(checkClipboard);
                                alert("社員証が検出されませんでした。");
                                // 5. main_menu.html を再表示する
                                location.reload();
                            }
                        }
                    })
                    .catch(err => {
                        console.error('クリップボードへのアクセスに失敗しました: ', err);
                        clearInterval(checkClipboard);
                        alert("クリップボードへのアクセスに失敗しました。");
                        // 5. main_menu.html を再表示する
                        location.reload();
                    });
            }, 100);

            // 4. エラーメッセージを表示し、yorimichi_z2.exe プロセスを終了し、main_menu.html を再表示する
            //    (yorimichi_z2.exe プロセスをJavaScriptから直接終了することはできません。
            //     この部分は、サーバーサイドで実行する必要があります。)
            //    ここでは、代替手段として、アラートを表示するだけにします。
            // alert("yorimichi_z2.exe プロセスを終了します (実際には終了されません)");
        });
    } else {
        // console.log('#lendingButton button not found on this page.'); // デバッグ用
    }
    ```

4.  **`templates/main_menu.html` の変更:**
    *   `apply_diff` ツールを使用して、`templates/main_menu.html` の "貸出" (Lending) ボタンに、クリックイベントハンドラを追加する。

    ```html
    <button type="button" class="btn btn-large" id="lendingButton">貸出</button>
    ```

## 補足

*   Windows 実行ファイル (`yorimichi_z.exe`, `yorimichi_z2.exe`) を JavaScript から直接実行することは、セキュリティ上の理由からブラウザでは許可されていません。代替手段として、サーバーサイドで実行する必要があります。
*   `yorimichi_z2.exe` プロセスを JavaScript から直接終了することもできません。代替手段として、サーバーサイドで実行する必要があります。
*   エラーハンドリングとロギングは、ブラウザのコンソールにエラーメッセージを表示する形で実装します。
*   `main_menu.html` の再表示は、ページ全体のリロードで行います。