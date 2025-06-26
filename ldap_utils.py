import os
import ssl
from ldap3 import Server, Connection, Tls, SASL, KERBEROS, ALL
from dotenv import load_dotenv

def get_ldap_user_info_python(gid):
    server_address = "LDAP.jp.sony.com"  # FQDNを使用
    root_ca_path = "/etc/ssl/certs/Sony_Root_CA2.cer"
    intermediate_ca_path = "/etc/ssl/certs/Sony_Intranet_CA2.cer"
    try:
        tls_configuration = Tls(
            validate=ssl.CERT_REQUIRED,
            version=ssl.PROTOCOL_TLS,
            ca_certs_file=root_ca_path,
            ca_certs_path=intermediate_ca_path
        )
        load_dotenv('.env')
        bind_dn = f"cn={os.getenv('UserName')},ou=Users,ou=JPUsers,dc=jp,dc=sony,dc=com"
        server = Server(server_address, port=636, use_ssl=True, tls=tls_configuration, get_info=ALL)
        conn = Connection(server, user=bind_dn, password=os.getenv('PASSWORD'), auto_bind=True)
        if not conn.bind():
            print(f"LDAP接続に失敗しました: {conn.result}")
            return None
        print("LDAP接続に成功しました。")
        search_base = "OU=Users,OU=JPUsers,DC=jp,DC=sony,DC=com"
        search_filter = f"(cn={gid})"
        attributes = ['mail', 'sn', 'givenName', 'department', 'company']
        if not conn.search(search_base, search_filter, attributes=attributes):
            print(f"LDAP検索に失敗しました: {conn.result}")
            return None
        if conn.entries:
            user_info = conn.entries[0]
            print(f"ユーザー情報が見つかりました: {user_info}")
            user_info = {
                "success": True,
                "ldap_val": True,
                "mail": user_info.mail.value if 'mail' in user_info else None,
            }
            return user_info
        else:
            print("指定したユーザーが見つかりませんでした。")
            return None
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return None
