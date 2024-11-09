// ==UserScript==
// @name         Douban Plugin
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Import a subject into database
// @author       Kingen
// @require      https://cdn.staticfile.org/jquery/3.4.1/jquery.min.js
// @match        https://movie.douban.com/subject/*/
// @match        https://movie.douban.com/subject/*/?*
// ==/UserScript==

const api = '/study/api/v1';


const parseWork = () => {
    const script = $('script[type="application/ld+json"]')
    const info = JSON.parse(script.text().replace(/\n/g, ''))
    return {
        'title': $('title').text().trim().slice(0, -5),
        'cover': info['image'],
        'duration': info['duration'],
        'releaseDate': info['datePublished'],
        'description': $('span[property="v:summary"]').text().trim(),
        'source': 'https://movie.douban.com' + info['url'],
        'actors': $('meta[property="video:actor"]').map((i, ele) => $(ele).attr('content').trim()).get(),
        'directors': $('meta[property="video:director"]').map((i, ele) => $(ele).attr('content').trim()).get(),
        'genres': info['genre'],
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
    putWork(work)
}

$(function () {
    const btn = $('<button type="button" style="margin-left: 30px; background-color: orange">导出</button>');
    btn.on('click', () => exportWork());
    $('#content h1').append(btn);
})