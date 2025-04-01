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
    const otherMainMenuButtons = document.querySelectorAll('.main-menu-header button:not(#gotoControlMenu), .main-menu-footer button');
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

// --- main_menu.html 用 ---
const lendingButtonElement = document.getElementById('lendingButton');
if (lendingButtonElement) {
    lendingButtonElement.addEventListener('click', () => {
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