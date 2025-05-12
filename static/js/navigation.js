document.addEventListener('DOMContentLoaded', () => {
    // --- main_menu.html 用 ---
    const gotoControlMenuButton = document.getElementById('gotoControlMenu');
    if (gotoControlMenuButton) {
        gotoControlMenuButton.addEventListener('click', () => {
            console.log('Navigating to /control_menu'); // デバッグ用ログ
            window.location.href = '/control_menu';
        });
    } else {
        // console.log('#gotoControlMenu button not found on this page.'); // デバッグ用
    }

    // --- control_menu.html 用 ---
    const gotoBookRegistrationButton = document.getElementById('gotoBookRegistration');
    if (gotoBookRegistrationButton) {
        gotoBookRegistrationButton.addEventListener('click', () => {
            console.log('Navigating to /book_registration'); // デバッグ用ログ
            window.location.href = '/book_registration';
        });
    } else {
        // console.log('#gotoBookRegistration button not found on this page.'); // デバッグ用
    }

    const gotoMainMenuButton = document.getElementById('gotoMainMenu');
    if (gotoMainMenuButton) {
        gotoMainMenuButton.addEventListener('click', () => {
            console.log('Navigating to /'); // デバッグ用ログ
            window.location.href = '/';
        });
    } else {
        // console.log('#gotoMainMenu button not found on this page.'); // デバッグ用
    }

    // --- (任意) その他のボタンに未実装を示すログを追加 ---
    // 例: main_menu.html の他のボタン
    const otherMainMenuButtons = document.querySelectorAll('.main-menu-header button:not(#gotoControlMenu), .main-menu-footer button:not(#lendingButton)');
    otherMainMenuButtons.forEach(button => {
        // 既にイベントリスナーが設定されているボタンは除外 (今回は不要だが念のため)
        if (button.id !== 'gotoControlMenu') {
            button.addEventListener('click', (event) => {
                // id がないボタン、または特定の id 以外のボタン
                if (!event.target.id || (event.target.id !== 'gotoControlMenu')) {
                     console.log(`Button "${event.target.textContent}" clicked, but no action is implemented yet.`);
                }
            });
        }
    });

    // 例: control_menu.html の他のボタン
    const otherControlMenuButtons = document.querySelectorAll('.control-menu-grid button:not(#gotoBookRegistration):not(#gotoMainMenu)');
    otherControlMenuButtons.forEach(button => {
         button.addEventListener('click', (event) => {
             console.log(`Button "${event.target.textContent}" clicked, but no action is implemented yet.`);
         });
    });

});
// --- scan_IDcard.html 用 ---
 const gotoMainMenuButton2 = document.getElementById('gotoMainMenu2');
 if (gotoMainMenuButton2) {
  gotoMainMenuButton2.addEventListener('click', () => {
   console.log('Navigating to /'); // デバッグ用ログ
   window.location.href = '/';
  });
 } else {
  // console.log('#gotoMainMenu button not found on this page.'); // デバッグ用
 }

// --- main_menu.html 用 ---
const lendingButtonElement = document.getElementById('lendingButton');
if (lendingButtonElement) {
    lendingButtonElement.addEventListener('click', () => {
        // 1. main_menu.html を非表示にする
        document.body.style.display = 'none';

        // 2. NFCプロンプトを表示する
        const nfcPrompt = document.createElement('img');
        nfcPrompt.src = '/static/images/IDCardTouchRequest.jpg';
        nfcPrompt.style.position = 'fixed';
        nfcPrompt.style.top = '50%';
        nfcPrompt.style.left = '50%';
        nfcPrompt.style.transform = 'translate(-50%, -50%)';
        nfcPrompt.style.maxWidth = '80%';
        nfcPrompt.style.maxHeight = '80%';
        nfcPrompt.id = 'nfcPrompt';
        document.body.appendChild(nfcPrompt);

        // 3. NFC読み取り処理
        let nfcReadTimeout;
        const readNFC = () => {
            // タイムアウト設定
            nfcReadTimeout = setTimeout(() => {
                // タイムアウト時の処理
                alert("社員証が検出されませんでした。");
                document.body.style.display = 'flex'; // main_menu.html を再表示
                const prompt = document.getElementById('nfcPrompt');
                if (prompt) {
                    prompt.remove();
                }
            }, 20000); // 20秒

            // NFC読み取り処理 (仮実装)
            // ここに nfcpy を使用した NFC 読み取り処理を実装する
            // 成功した場合:
            //   - clearTimeout(nfcReadTimeout);
            //   - nfcPrompt.remove();
            //   - 社員番号と氏名をコンソールに出力
            //   - (今回はQRコードリーダーは表示しない)
            // 失敗した場合:
            //   - エラーメッセージを表示
            //   - main_menu.html を再表示

            // **注意**: nfcpy はブラウザで直接実行できないため、
            //       サーバーサイドで NFC 読み取り処理を行う必要があります。
            //       このコードはあくまでクライアントサイドのUI制御の例です。

            // 例: (サーバーサイドからデータを受け取ることを想定)
            fetch('/read_nfc')
                .then(response => response.json())
                .then(data => {
                    clearTimeout(nfcReadTimeout);
                    const prompt = document.getElementById('nfcPrompt');
                    if (prompt) {
                        prompt.remove();
                    }
                    if (data.status === 'success') {
                        console.log("社員番号: " + data.employee_id);
                        console.log("氏名: " + data.name);
                    } else {
                        alert("NFC読み取りエラー: " + data.message);
                        document.body.style.display = 'flex'; // main_menu.html を再表示
                    }
                })
                .catch(error => {
                    clearTimeout(nfcReadTimeout);
                    console.error('NFC読み取りエラー:', error);
                    alert("NFC読み取りエラーが発生しました。");
                    document.body.style.display = 'flex'; // main_menu.html を再表示
                    const prompt = document.getElementById('nfcPrompt');
                    if (prompt) {
                        prompt.remove();
                    }
                });
        };

        readNFC();
    });
} else {
    // console.log('#lendingButton button not found on this page.'); // デバッグ用
}