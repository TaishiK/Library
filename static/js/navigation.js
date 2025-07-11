document.addEventListener('DOMContentLoaded', () => {
    // --- main_menu.html 用 ---
    const gotoControlMenuButton = document.getElementById('gotoControlMenu');
    if (gotoControlMenuButton) {
        gotoControlMenuButton.addEventListener('click', () => {
            console.log('Navigating to /control_menu'); // デバッグ用ログ
            localStorage.FlagID = 'CONTROL';
            window.location.href = '/scan_IDcard.html';
        });
    } else {
        // console.log('#gotoControlMenu button not found on this page.'); // デバッグ用
    }
    const lendingButton = document.getElementById('lendingButton');
    if (lendingButton) {
        lendingButton.addEventListener('click', () => {
            console.log('Navigating to /scan_IDcard'); // デバッグ用ログ
            localStorage.FlagID = 'LEND';
            localStorage.FlagQR = 'LEND';
            window.location.href = '/scan_IDcard.html';
        });
    }
    const returnButton = document.getElementById('returnButton');
    if (returnButton) {
        returnButton.addEventListener('click', () => {
            localStorage.FlagQR = 'RETURN';
            window.location.href = '/scan_QRcode.html';
        });
    }

    const shelfCheckButton = document.getElementById('shelfCheckButton');
    if (shelfCheckButton) {
        shelfCheckButton.addEventListener('click', () => {
            localStorage.FlagQR = 'SHELF';
            window.location.href = '/scan_QRcode.html';
        });
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

    const registerAdministratorButton = document.getElementById('registerAdministratorButton');
    if (registerAdministratorButton) {
        registerAdministratorButton.addEventListener('click', () => {
            console.log('管理者追加登録ボタンがクリックされました。');
            showCustomAlert('新しく管理者になる人の社員証でタッチして下さい。', 1, (result) => {
                if (result === 'ok') {
                    localStorage.FlagID = 'ADMINISTRATOR';
                    window.location.href = '/scan_IDcard.html';
                }
            });
        });
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


