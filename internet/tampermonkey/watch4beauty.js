// ==UserScript==
// @name         Watch4beauty Plugin
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Export work into database
// @author       Kingen
// @require      https://cdn.staticfile.org/jquery/3.4.1/jquery.min.js
// @match        https://www.watch4beauty.com/updates/**
// ==/UserScript==

const api = '/study/api/v1';
const durationRegex = /((\d{1,2}:)?\d{1,2}:\d{1,2}) FILM/;
const releaseRegex = /Published (\d{4})\.(\d{1,2})\.(\d{1,2})/;

const parseWork = () => {
    if ($('#lightbox-info').length === 0) {
        alert('请先打开作品详情页')
        return
    }
    const cover = $('#gallcover .loadable-data img').attr('src')
    const dateMatch = $('.issue-detail > .link').text().trim().match(releaseRegex);
    const year = dateMatch[1];
    const month = dateMatch[2].padStart(2, '0');
    const day = dateMatch[3].padStart(2, '0');
    const durationMatch = $('.issue-detail .hero:first').text().trim().match(durationRegex)

    return {
        'title': document.title.substring(5),
        'cover': cover.includes('wide') ? cover.replace('cover-wide-2560.', 'cover-960.') : cover,
        'cover2': cover.includes('wide') ? cover : $('video').attr('poster'),
        'duration': durationMatch ? durationMatch[1] : null,
        'releaseDate': `${year}-${month}-${day}`,
        'producer': 'Watch4beauty',
        'source': window.location.href,
        'actors': $('#lightbox-info p:eq(2) a').map((i, ele) => $(ele).text().trim()).get(),
        'genres': $('a.tag').map((i, ele) => $(ele).text().trim()).get(),
    }
}

const putWork = work => {
    console.log('save work', work);
    fetch(`${api}/works/none?merge=1`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(work)
    }).then(response => {
        if (response.status === 200 || response.status === 201) {
            const text = response.status === 200 ? '已更新' : '已添加';
            response.json().then(
                result => {
                    console.log('success', result);
                    alert(`${text}：${result['id']}`);
                }
            )
        } else if (response.status === 204) {
            alert('已忽略')
        } else if (response.status === 409) {
            response.json().then(
                result => {
                    console.log('conflict', result['data']);
                    alert('有冲突，请查看控制台');
                }
            )
        } else {
            response.text().then(text => {
                console.log('failed to save', text);
                alert('更新失败：' + text);
            })
        }
    }).catch(reason => {
        alert(reason)
    })
}

const exportWork = () => {
    const work = parseWork();
    if (work) {
        putWork(work)
    }
}

$(async function () {
    const btn = $('<span style="position: fixed; top: 120px; right: 40px; cursor: pointer; color: orange; z-index: 999">导出</span>');
    btn.on('click', () => exportWork());
    $('#root').append(btn);
})
