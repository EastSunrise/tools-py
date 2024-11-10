// ==UserScript==
// @name         TeenDreams Plugin
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Export work into database
// @author       Kingen
// @require      https://cdn.staticfile.org/jquery/3.4.1/jquery.min.js
// @match        https://www.teendreams.com/t4/**
// ==/UserScript==

const api = '/study/api/v1';
const srcRegex = /src="([^"]*)"/;
const posterRegex = /poster="([^"]*)"/;

const formatURL = url => {
    return new URL(url, window.location.href).href
}

const parseWork = () => {
    const script = $('.innerOld > script').text()

    return {
        'title': $('meta[property="og:title"]').attr('content').trim(),
        'cover2': formatURL(script.match(posterRegex)[1].replace('-1x.', '-4x.')),
        'duration': $('.player-time').text().split('/')[1].trim(),
        'releaseDate': $('.content-date').text().trim().split(':')[1].trim(),
        'producer': 'TeenDreams',
        'trailer': formatURL(script.match(srcRegex)[1]),
        'source': window.location.href,
        'actors': $('.item-name').text().trim(),
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
    const btn = $('<li><button style="color: orange">导出</button></li>');
    btn.on('click', () => exportWork());
    $('#social-tabs > ul').append(btn);
})
