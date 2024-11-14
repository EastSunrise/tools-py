// ==UserScript==
// @name         Wow Network Plugin
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Export work into database
// @author       Kingen
// @require      https://cdn.staticfile.org/jquery/3.4.1/jquery.min.js
// @match        https://venus.allfinegirls.com/girl/**
// @match        https://venus.wowgirls.com/girl/**
// ==/UserScript==

const api = '/study/api/v1';

const formatURL = url => {
    return new URL(url, window.location.href).href
}

const parseWork = ele => {
    return {
        'title': $(ele).find('a.title').text().trim(),
        'cover': null,
        'cover2': $(ele).find('.thumb img').attr('src'),
        'duration': null,
        'releaseDate': null,
        'producer': null,
        'description': null,
        'images': null,
        'trailer': null,
        'source': [window.location.href, formatURL($(ele).find('a.title').attr('href'))],
        'actors': $(ele).find('.models a').map((i, ele) => $(ele).text().trim()).get(),
        'directors': null,
        'genres': $(ele).find('.genres a').map((i, ele) => $(ele).text().trim()).get(),
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

const exportWork = (ele) => {
    const work = parseWork(ele);
    if (work) {
        putWork(work)
    }
}

$(function () {
    setInterval(() => {
        $('.cf_content_list div').each((i, ele) => {
            if ($(ele).find('#my-export').length === 0) {
                const btn = $('<button id="my-export" style="position: absolute; top: 10px; right: 10px; color: orange; z-index: 9999">导出</button>');
                $(ele).append(btn);
                btn.on('click', () => exportWork($(ele)));
            }
        })
    }, 500)
})
