# /templates/scan_IDcard.html に「戻る」ボタンを追加する計画

## 概要

/templates/scan_IDcard.html テンプレートに「戻る」ボタンを追加します。このボタンをクリックすると、現在の /templates/scan_IDcard.html ビューが閉じられ、/templates/main_menu.html テンプレートが表示されます。

## 詳細

1.  **配置場所:** ページの左上
2.  **スタイル:** /templates/main_menu.html のヘッダーにあるボタンのスタイル（`btn btn-small` クラス）に合わせる
3.  **遷移方法:** JavaScript を使用してクライアント側で処理する

## 手順

1.  **/templates/scan_IDcard.html を修正:**

    *   ページの左上に「戻る」ボタンを追加します。
    *   ボタンのスタイルを `/templates/main_menu.html` のヘッダーにあるボタンのスタイルに合わせます。

2.  **static/js/navigation.js を修正:**

    *   「戻る」ボタンがクリックされたときに、`/templates/main_menu.html` に遷移する JavaScript コードを追加します。

3.  **テスト:**

    *   「戻る」ボタンが正しく表示されることを確認します。
    *   「戻る」ボタンをクリックすると、`/templates/main_menu.html` に正しく遷移することを確認します。

## 図

```mermaid
graph LR
    A[開始] --> B{情報の収集};
    B --> C{質問};
    C --> D{詳細な計画};
    D --> E{/templates/scan_IDcard.html の内容を確認};
    E --> F{/templates/main_menu.html の内容を確認};
    F --> G{app.py の内容を確認};
    G --> H{static/js/navigation.js の内容を確認};
    H --> I{「戻る」ボタンの配置場所をページの左上に決定};
    I --> J{「戻る」ボタンのスタイルを main_menu.html のヘッダーにあるボタンのスタイルに合わせる};
    J --> K{遷移方法を JavaScript を使用してクライアント側で処理することに決定};
    K --> L{/templates/scan_IDcard.html を修正};
    L --> M{static/js/navigation.js を修正};
    M --> N[テスト];
    N --> O[問題がなければ完了];
    O --> P[完了];