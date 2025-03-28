# 書籍データ登録システム開発計画

## 概要

Accessで作成された書籍登録フォームを参考に、HTML、CSS、JavaScriptを用いて、クライアントサイドで動作する書籍データ登録システムを開発します。

## 機能要件

*   書籍データの登録
    *   InstanceID (自動生成)
    *   ISBN
    *   Title
    *   Author
    *   Publisher
    *   IssueYear
    *   Price
*   ローカルストレージへのデータ保存
*   テーブル形式でのデータ表示
*   データ永続性
*   入力データの検証
*   エラー処理

## 技術要件

*   単一HTMLファイル
*   HTML/CSS/JavaScriptのみ使用
*   サーバーサイドコード不要

## 計画

1.  **UIデザインの検討:**
    *   `/LibraryPages/BookRegister.png` を参考に、HTMLとCSSで同様のUIを再現する。
    *   使いやすさ、アクセシビリティを考慮する。
2.  **HTML構造の設計:**
    *   書籍データ入力フォームの作成 (Accessのフォームを参考に)
    *   書籍データ表示テーブルの作成
    *   CSSスタイルの適用
3.  **JavaScriptロジックの設計:**
    *   `InstanceID`の自動生成ロジック
    *   入力データの検証ロジック
    *   `localStorage`へのデータ保存ロジック
    *   テーブルへのデータ表示ロジック
    *   エラー処理ロジック
4.  **初期データの作成:**
    *   10件のサンプルデータを作成
5.  **単一HTMLファイルへの統合:**
    *   HTML、CSS、JavaScriptを単一のHTMLファイルに統合
6.  **テスト:**
    *   動作確認
    *   データ永続性の確認
    *   エラー処理の確認

## Mermaid図

```mermaid
graph LR
    A[UIデザイン検討] --> B{HTML構造設計};
    B --> C{JavaScriptロジック設計};
    C --> D{初期データ作成};
    D --> E{単一HTMLファイル統合};
    E --> F{テスト};
    F --> G[完了];
    A -- 参考 --> Accessフォーム;
    B -- 入力フィールド --> InstanceID, ISBN, Title, Author, Publisher, IssueYear, Price;
    C -- ロジック --> InstanceID自動生成, データ検証, localStorage保存, データ表示, エラー処理;
    D -- データ --> 10件のサンプルデータ;