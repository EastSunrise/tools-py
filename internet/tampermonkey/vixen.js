// ==UserScript==
// @name         VIXEN Plugin
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Export work into database
// @author       Kingen
// @require      https://cdn.staticfile.org/jquery/3.4.1/jquery.min.js
// @match        https://www.vixen.com/videos/**
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
    const props = JSON.parse($('script#__NEXT_DATA__').text())['props']['pageProps']
    const posters = [...props['video']['images']['poster']]
    const maxPoster = posters.reduce((max, obj) => (obj['width'] > max['width'] ? obj : max), posters[0])

    return {
        'title': props['title'],
        'cover': props['structuredData']['thumbnailUrl'],
        'cover2': maxPoster['highdpi'] ? maxPoster['highdpi']['double'] : maxPoster['src'],
        'duration': props['structuredData']['duration'],
        'releaseDate': formatDate($('[title="Release date"] span').text().trim()),
        'producer': 'VIXEN',
        'description': props['description'],
        'images': props['galleryImages'].map(img => img['src']),
        'trailer': null,
        'source': window.location.href,
        'actors': props['video']['modelsSlugged'].map(x => x['name']),
        'directors': props['video']['directors'].map(x => x['name']),
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
    const btn = $('<span style="cursor: pointer; font-size: 2rem; margin-left: 20px">导出</span>');
    btn.on('click', () => exportWork());
    $('nav').append(btn);
})
