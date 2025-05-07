# FeliCa カードリーダーの修正計画

## 概要

`/templates/read_IDcard.html` を修正して、ID カードのタップを継続的にリッスンするようにします。これにより、NFC リーダーに事前にカードを配置する必要がなくなります。

## 現在の実装の問題点

現在の実装は、`/templates/read_IDcard.html` の 46-49 行目にあり、ID カードの値を正常に読み取りますが、カードがすでに提示されている場合に限ります。

## 修正計画

1.  `FeliCa` ボタンのクリックイベントリスナーを削除します。
2.  ページがロードされたときに `felica_card()` 関数を呼び出すようにします。
3.  `felica_card()` 関数内で、ID カードのタップを継続的にリッスンするループを実装します。
4.  ループが効率的であり、リソースを過剰に消費しないように、適切な待機時間 (例: 100ms) を設定します。
5.  カードが提示されない場合に無期限の待機を防ぐために、タイムアウトメカニズムを追加することを検討します。

## 修正後のコード例

```html
<!DOCTYPE html>
<html>
<head>
  <title>FeliCa Card Reader</title>
</head>
<body>
  <h1>FeliCa Card Reader</h1>
  <p id="status">Waiting for card...</p>

  <script>
    async function felica_card() {
      console.log('[Reading a FeliCa Card] Begin');

      let lib = null;

      detectTitle.innerText = '';

      if (!("NDEFReader" in window)) {
        alert("Web NFC is not supported in this browser.");
        return;
      }

      try {
        const ndef = new NDEFReader();
        await ndef.scan();

        console.log("NFC scan started.");

        ndef.onreadingerror = (event) => {
          console.log("Error! Scan failed to read message.");
        };

        ndef.onreading = async (event) => {
          const message = event.message;
          console.log(`  > Records: (${message.records.length})`);

          for (const record of message.records) {
            console.log(`  > Record Type: ${record.recordType}`);
            console.log(`  > MIME Type: ${record.mediaType}`);
            console.log(`  > Data: ${new TextDecoder().decode(record.data)}`);
          }
        };
      } catch (error) {
        console.log("Argh! " + error);
      }

      // タイムアウトメカニズム (例: 30秒)
      setTimeout(() => {
        console.log("Timeout: No card detected.");
        // タイムアウト時の処理 (例: エラーメッセージの表示)
        document.getElementById("status").textContent = "Timeout: No card detected.";
      }, 30000);
    }

    // ページがロードされたときに felica_card() 関数を呼び出す
    window.onload = felica_card;
  </script>
</body>
</html>