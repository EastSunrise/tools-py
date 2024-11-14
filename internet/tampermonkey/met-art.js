// ==UserScript==
// @name         MetArt Group Plugin
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Export work into database
// @author       Kingen
// @require      https://cdn.staticfile.org/jquery/3.4.1/jquery.min.js
// @match        https://www.straplez.com/model/*/movie/**
// @match        https://www.metartx.com/model/*/movie/**
// ==/UserScript==

const api = '/study/api/v1';
const imgRegex = /url\((&quot;|")(.*?)(&quot;|")\);/;

const parseWork = () => {
    const info = {}
    $('ul[data-testid="movie-data"] li').each(function () {
        const key = $(this).find('span:first').text().trim();
        info[key] = $(this).find('span:last');
    });
    const img = $('.cover-image');
    let cover2 = null;
    if (img.length > 0) {
        cover2 = img.attr('src');
    } else {
        const matches = $('div.jw-preview').attr('style').match(imgRegex);
        if (matches && matches[2]) {
            cover2 = matches[2];
        } else {
            alert('封面获取失败！')
            return;
        }
    }

    return {
        'title': $('ol.container li:last').text().trim(),
        'cover': $('.movie-details .panel-content img').attr('src'),
        'cover2': cover2,
        'duration': parseInt($('meta[property="og:video:duration"]').attr('content')),
        'releaseDate': $('meta[property="og:video:release_date"]').attr('content').split('T')[0], // UTC-08:00
        'producer': $('.logo img').attr('alt'),
        'description': null,
        'images': null,
        'trailer': null,
        'source': window.location.href,
        'actors': info['Cast:'].find('a').map((i, ele) => $(ele).text().trim()).get(),
        'directors': info['Director:'].find('a').map((i, ele) => $(ele).text().trim()).get(),
        'genres': $('meta[property="og:video:tag"]').map((i, ele) => $(ele).attr('content')).get(),
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
    const btn = $('<div class="btn btn-primary join-btn" style="position: fixed; right: 50px">导出</div>');
    btn.on('click', () => exportWork());
    $('.navbar .va-m > div').append(btn);
})
