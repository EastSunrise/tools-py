// ==UserScript==
// @name         X-Art Plugin
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Export work into database
// @author       Kingen
// @require      https://cdn.staticfile.org/jquery/3.4.1/jquery.min.js
// @match        https://www.x-art.com/videos/**
// ==/UserScript==

const api = '/study/api/v1';

// Formats English date string to YYYY-MM-DD
const formatDate = (str) => {
    const date = new Date(str);
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    return `${year}-${month}-${day}`;
}

const parseWork = () => {
    return {
        'title': $('.info.row h1').text().trim(),
        'cover': null,
        'cover2': $('#thumb').attr('value'),
        'duration': null,
        'releaseDate': formatDate($('.info > h2:first').text().trim()),
        'producer': 'X-Art',
        'description': $('.info p').text().trim(),
        'images': $('.gallery-block img').map((i, ele) => $(ele).attr('src')).get(),
        'trailer': null,
        'source': window.location.href,
        'actors': $('.info > h2:eq(1) a').map((i, ele) => $(ele).text().trim()).get(),
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
    const btn = $('<li><button style="background-color: #fd01f1">导出</button></li>');
    btn.on('click', () => exportWork());
    $('.show-for-large-up.middle-menu').append(btn);
})
