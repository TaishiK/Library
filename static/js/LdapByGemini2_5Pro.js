const ldap = require('ldapjs');

/**
 * LDAPサーバーから指定されたGID (社員番号) のユーザー情報を取得します。
 * SASL GSSAPI (Kerberos) 認証を試み、成功すればユーザー名・パスワードなしで接続します。
 *
 * @param {string} gid 検索するユーザーのGID (社員番号)
 * @returns {Promise<object>} ユーザー情報、またはエラー情報を含むオブジェクト
 */
async function getLdapUserInfoJs(gid) {
    // VBAコードから推測される設定値 (実際の環境に合わせて調整してください)
    const ldapServerUrl = 'ldaps://LDAP.jp.sony.com'; // ADS_USE_SSLからLDAPSと判断
    const baseDnForSearch = 'OU=Users,OU=JPUsers,DC=jp,DC=sony,DC=com';
    // VBAではCN (Common Name) にGIDが設定されていると仮定してDNを構築
    const userDn = `CN=${gid},${baseDnForSearch}`;

    const client = ldap.createClient({
        url: ldapServerUrl,
        tlsOptions: {
            // 本番環境では、サーバー証明書を適切に検証してください。
            // 自己署名証明書やプライベートCAの場合は、ca, cert, keyなどのオプション設定が必要な場合があります。
            // 一般的なドメイン認証局発行の証明書であれば、Node.jsのデフォルトCAストアで検証されることが多いです。
            rejectUnauthorized: false, // セキュリティのためtrueを推奨。接続に失敗する場合は証明書関連の問題を確認してください。
            // host: 'LDAP.jp.sony.com' // SNI (Server Name Indication) のためにホスト名を明示することが役立つ場合があります
        },
        connectTimeout: 10000, // 接続タイムアウト (ミリ秒)
        timeout: 15000,        // 操作タイムアウト (ミリ秒)
    });

    // グローバルなクライアントエラーハンドリング (デバッグ用)
    // client.on('error', (err) => {
    //     console.error('[LDAP Client Global Error]', err);
    // });

    const bindPromise = new Promise((resolve, reject) => {
        // SASL GSSAPI (Kerberos) を使用してバインドします。
        // これにより、Node.jsプロセスを実行しているユーザーの資格情報が (環境が正しく設定されていれば) 使用されます。
        // optionsオブジェクトは空で良い場合が多いですが、必要に応じて設定を追加できます。
        client.sasl.gssapi({}, (err) => {
            if (err) {
                let errorMessage = `LDAP SASL/GSSAPI Bind failed: ${err.ldapMessage || err.message}`;
                if (err.code && (err.code === 82 || err.code === ldap.LDAP_LOCAL_ERROR || (err.message && err.message.toLowerCase().includes("kerberos")))) {
                     errorMessage += ' (This likely indicates a Kerberos configuration issue, invalid/expired ticket, or problem connecting to the KDC. Ensure `kinit` was run if on Linux/macOS, or the process is running as a domain user on Windows.)';
                }
                console.error('[LDAP Bind Error]', errorMessage, err);
                reject(new Error(errorMessage));
                return;
            }
            console.log('LDAP SASL/GSSAPI Bind successful.');
            resolve();
        });
    });

    try {
        await bindPromise; // Bind処理の完了を待つ

        const searchOptions = {
            scope: 'base', // 特定のDNのオブジェクトを取得するため 'base' を指定
            attributes: [ // VBAコードで参照・コメントアウトされていた属性
                'mail',
                'sn',         // 姓
                'givenName',  // 名
                'displayName',
                'telephoneNumber',
                'physicalDeliveryOfficeName',
                'department',
                'streetAddress',
                'l',          // 市区町村
                'st',         // 都道府県
                'company'
            ],
            // filterはscope: 'base' の場合、DNで直接指定するため通常不要
        };

        const user = await new Promise((resolve, reject) => {
            // userDnで指定されたオブジェクトを検索
            client.search(userDn, searchOptions, (err, res) => {
                if (err) {
                    const errMsg = `LDAP search initialization failed for DN "${userDn}": ${err.message}`;
                    console.error('[LDAP Search Init Error]', errMsg, err);
                    reject(new Error(errMsg));
                    return;
                }

                let foundUser = null;
                let searchError = null;

                res.on('searchEntry', (entry) => {
                    // console.log('LDAP Entry found:', JSON.stringify(entry.object));
                    if (foundUser) {
                        // scope 'base' で複数のエントリが返ることは通常ないはずですが、念のため警告
                        console.warn("Multiple entries found for a base DN search. Using the first one.");
                    } else {
                        foundUser = entry.object;
                    }
                });

                res.on('error', (errStream) => {
                    // ストリームエラーが発生した場合
                    searchError = new Error(`LDAP search stream error for DN "${userDn}": ${errStream.message}`);
                    console.error('[LDAP Search Stream Error]', searchError.message, errStream);
                    reject(searchError);
                });

                res.on('end', (result) => {
                    if (searchError) return; // 既にストリームエラーでrejectされていれば何もしない

                    if (result && result.status !== 0 && !foundUser) {
                        // 検索が成功ステータス(0)以外で終了し、かつユーザーが見つからなかった場合
                        const errMsg = `LDAP search for DN "${userDn}" finished with non-zero status: ${result.status} (${result.errorMessage || 'No specific error message from server'}). Review LDAP server logs for details.`;
                        console.error('[LDAP Search End Error]', errMsg, result);
                        reject(new Error(errMsg));
                        return;
                    }
                    if (!foundUser) {
                        // 検索が正常に終了したが、エントリが見つからなかった場合
                        reject(new Error(`User not found with DN "${userDn}"`));
                        return;
                    }
                    resolve(foundUser); // ユーザーオブジェクトを解決
                });
            });
        });

        // VBAの戻り値の形式に合わせて整形 (必要に応じて変更)
        return {
            success: true,
            ldap_val: true, // VBAのLDAP_valに相当
            pstrMail_ad: user.mail,
            pstrFamily_Name: user.sn,
            pstrGiven_Name: user.givenName,
            // 他の取得した属性も返す
            displayName: user.displayName,
            telephoneNumber: user.telephoneNumber,
            physicalDeliveryOfficeName: user.physicalDeliveryOfficeName,
            department: user.department,
            streetAddress: user.streetAddress,
            l: user.l,
            st: user.st,
            company: user.company,
            raw: user // 全ての取得属性を保持
        };

    } catch (error) {
        // BindエラーまたはSearchエラー、その他の予期せぬエラー
        console.error('[Main LDAP Function Error]', error.message, error.stack);
        return {
            success: false,
            ldap_val: false, // エラー時はfalse
            error: error.message
        };
    } finally {
        // クライアントが接続状態であればアンバインド
        if (client && client.connected) {
            client.unbind((unbindErr) => {
                if (unbindErr) {
                    console.error('[LDAP Unbind Error]', unbindErr.message);
                } else {
                    // console.log('LDAP Unbind successful.');
                }
            });
        } else if (client) {
            // 既に接続が切れているか、破棄されている場合
            // console.log('LDAP client was not connected at finally, or already destroyed.');
        }
    }
}

// --- Node.jsでの実行例 ---

async function testLdapSearch() {
    const employeeId = "0000920442";  // ここに検索したい社員番号(GID)を入力してください

    console.log(`\nAttempting to fetch LDAP information for GID: ${employeeId}`);
    const userInfo = await getLdapUserInfoJs(employeeId);

    if (userInfo.success) {
        console.log("\n--- User Information Fetched Successfully ---");
        console.log(`LDAP Connection Status (ldap_val): ${userInfo.ldap_val}`);
        console.log(`Email (pstrMail_ad): ${userInfo.pstrMail_ad}`);
        console.log(`Family Name (pstrFamily_Name): ${userInfo.pstrFamily_Name}`);
        console.log(`Given Name (pstrGiven_Name): ${userInfo.pstrGiven_Name}`);
        console.log(`Display Name: ${userInfo.displayName}`);
        console.log(`Company: ${userInfo.company}`);
        // console.log('Raw Data:', userInfo.raw); // 全データ表示
        console.log("-------------------------------------------\n");
    } else {
        console.error("\n--- Failed to Fetch User Information ---");
        console.error(`LDAP Connection Status (ldap_val): ${userInfo.ldap_val}`);
        console.error(`Error: ${userInfo.error}`);
        console.error("--------------------------------------\n");
        console.error("Troubleshooting tips for SASL/GSSAPI (Kerberos) errors:");
        console.error("1. Ensure Node.js is running under a user context with a valid Kerberos ticket.");
        console.error("   - On Windows: Ensure the script is run as a domain user with permissions to access LDAP.");
        console.error("   - On Linux/macOS: Use 'kinit <username>' to obtain a Kerberos ticket before running the script.");
        console.error("2. Verify your system's Kerberos configuration (e.g., /etc/krb5.conf on Linux, or domain settings on Windows).");
        console.error("3. Check network connectivity to the Kerberos KDC and the LDAP server (LDAP.jp.sony.com on port 636).");
        console.error("4. Ensure the LDAP server is configured to support SASL/GSSAPI authentication.");
        console.error("5. If you still face issues, detailed logs from the LDAP server переговоров and client-side Kerberos logs might be needed.");
    }
}

// テスト実行
testLdapSearch();


// モジュールとしてエクスポートする場合は以下を有効化
// module.exports = { getLdapUserInfoJs };