// ==UserScript==
// @name         WowGirls Plugin
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Export work into database
// @author       Kingen
// @require      https://cdn.staticfile.org/jquery/3.4.1/jquery.min.js
// @match        https://www.wowgirlsblog.com/**
// ==/UserScript==

const api = '/study/api/v1';

const parseWork = () => {
    const info = JSON.parse($('.flowplayer').attr('data-item'))
    console.log(info)

    return {
        'title': $('meta[itemprop="name"]').attr('content'),
        'cover': null,
        'cover2': $('meta[property="og:image"]').attr('content'),
        'duration': $('meta[itemprop="duration"]').attr('content'),
        'releaseDate': $('meta[itemprop="uploadDate"]').attr('content').split('T')[0],
        'producer': 'WowGirls',
        'description': null,
        'images': null,
        'trailer': info['sources'][0]['src'],
        'source': window.location.href,
        'actors': $('#video-actors a').map((i, ele) => $(ele).text().trim()).get(),
        'directors': null,
        'genres': null,
        'series': null
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

$(function () {
    const btn = $('<button style="position: fixed; top: 0; right: 60px; color: orange">导出</button>');
    btn.on('click', () => exportWork());
    $('#page').append(btn);
})
