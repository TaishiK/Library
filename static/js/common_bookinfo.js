// 書籍情報取得API（exec_borrow.html, exec_return.html 共通）
async function fetchBookInfo(instID) {
    const res = await fetch(`/api/instance_info/${encodeURIComponent(instID)}`);
    if (!res.ok) return null;
    return await res.json();
}

// detailsId, thumbAreaIdはID名（例: 'bookDetails'）で渡す
async function showBookInfo(instID, detailsId, thumbAreaId) {
    console.log('showBookInfo called with instID:', instID); // デバッグ用ログ
    const details = document.getElementById(detailsId);
    const thumbArea = document.getElementById(thumbAreaId);
    if (!instID) {
        details.innerHTML = '<p>インスタンスIDが指定されていません。</p>';
        thumbArea.innerHTML = '';
        return;
    }
    const data = await fetchBookInfo(instID);
    console.log('Fetched book info:', data); // デバッグ用ログ
    if (!data || !data.success) {
        details.innerHTML = '<p>該当する書籍情報が見つかりません。</p>';
        thumbArea.innerHTML = '';
        return;
    }
    // 書籍情報表示
    details.innerHTML = `
        <div><b>インスタンスID:</b> ${data.instance_id}</div>
        <div><b>ISBN:</b> ${data.isbn}</div>
        <div><b>書籍名:</b> ${data.title}</div>
        <div><b>著者:</b> ${data.author}</div>
        <div><b>出版社:</b> ${data.publisher}</div>
        <div><b>発行年:</b> ${data.issue_year}</div>
    `;
    // サムネイル表示
    if (data.thumbnail_exists && data.thumbnail_url) {
        thumbArea.innerHTML = `<img src="${data.thumbnail_url}" alt="書影" class="thumbnail-img">`;
    } else {
        thumbArea.innerHTML = '<div>該当の書影はありません</div>';
    }
}
