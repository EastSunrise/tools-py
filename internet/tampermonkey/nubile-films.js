// ==UserScript==
// @name         Nubile Films Plugin
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Export work into database
// @author       Kingen
// @require      https://cdn.staticfile.org/jquery/3.4.1/jquery.min.js
// @match        https://nubilefilms.com/video/watch/**
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
    const desc = $('.content-pane-description')
    let description;
    if ($(desc).find('p').length > 0) {
        description = $(desc).find('p').map((i, ele) => $(ele).text().trim()).get().join('\n');
    } else {
        description = desc.text().trim();
    }

    return {
        'title': $('.content-pane-title h2').text().trim(),
        'cover': null,
        'cover2': $('video').attr('poster'),
        'duration': null,
        'releaseDate': formatDate($('.content-pane-title span.date').text().trim()),
        'producer': $('meta[property="og:site_name"]').attr('content'),
        'description': description,
        'images': null,
        'trailer': $('video').attr('src'),
        'source': window.location.href,
        'actors': $('.content-pane-performers a').map((i, ele) => $(ele).text().trim()).get(),
        'directors': null,
        'genres': $('.categories a').map((i, ele) => $(ele).text().trim()).get(),
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
    const btn = $('<li class="nav-item" style="margin-right: 20px"><span class="btn btn-cta btn-sm w-100 w-md-auto" style="cursor: pointer">导出</span></li>');
    btn.on('click', () => exportWork());
    $('.nav-right').prepend(btn);
})
