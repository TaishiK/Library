# `/templates/scan_IDcard.html` の画像中央表示計画

## 目的
`/templates/scan_IDcard.html` を編集し、画像ファイル `/static/images/IDCardTouchRequest.jpg` がブラウザ画面の垂直方向および水平方向の中央に表示されるようにCSSを適用する。

## 計画

1.  `/templates/scan_IDcard.html` に、`/static/images/IDCardTouchRequest.jpg` を表示するための `<img>` タグを追加します。既存のコンテンツ（戻るボタンやメッセージ表示エリア）の下に配置することを想定しています。
    -   追加箇所: `<div class="mainArea">` タグの終了後、スクリプトタグの前に `<img src="/static/images/IDCardTouchRequest.jpg" alt="ID Card Touch Request" class="centered-image">` を挿入します。

2.  `/static/css/scan_idcard.css` に、画像要素を垂直方向および水平方向の中央に配置するためのCSSスタイルを追加します。
    -   `body` 要素に以下のスタイルを追加または変更します。
        ```css
        body {
          display: flex; /* bodyをFlexboxコンテナにする */
          flex-direction: column; /* 子要素を縦方向に並べる */
          justify-content: center; /* 垂直方向の中央揃え */
          align-items: center; /* 水平方向の中央揃え */
          min-height: 100vh; /* bodyの高さをビューポートの高さに合わせる */
          margin: 0; /* デフォルトのマージンをリセット */
        }
        ```
    -   追加した画像タグに指定したクラス (`centered-image`) に対して、以下のスタイルを追加します。
        ```css
        .centered-image {
          max-width: 100%; /* 画像がコンテナからはみ出さないように調整 */
          height: auto; /* アスペクト比を維持 */
        }
        ```

## 変更内容のイメージ

### `/templates/scan_IDcard.html` (変更箇所抜粋)

```html
 ... 既存のコンテンツ ...
 42 |  </div>
 43 | 
 44 |  <!-- ここに画像タグを追加 -->
 45 |  <img src="/static/images/IDCardTouchRequest.jpg" alt="ID Card Touch Request" class="centered-image">
 46 | 
 ... スクリプトタグなど ...
```

### `/static/css/scan_idcard.css` (追加するスタイル)

```css
/* 画像を中央に配置するためのスタイル */
body {
  display: flex; /* bodyをFlexboxコンテナにする */
  flex-direction: column; /* 子要素を縦方向に並べる */
  justify-content: center; /* 垂直方向の中央揃え */
  align-items: center; /* 水平方向の中央揃え */
  min-height: 100vh; /* bodyの高さをビューポートの高さに合わせる */
  margin: 0; /* デフォルトのマージンをリセット */
}

.centered-image {
  max-width: 100%; /* 画像がコンテナからはみ出さないように調整 */
  height: auto; /* アスペクト比を維持 */
}

/* 既存のスタイルも維持されます */
```

## 実装について

この計画を実行するには、HTMLファイルとCSSファイルを編集できるモードに切り替える必要があります。