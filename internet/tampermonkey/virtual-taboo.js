// ==UserScript==
// @name         Virtual Taboo Plugin
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Export work into database
// @author       Kingen
// @require      https://cdn.staticfile.org/jquery/3.4.1/jquery.min.js
// @match        https://virtualtaboo.com/videos/**
// ==/UserScript==

const api = '/study/api/v1';
const durationRegex = /(\d+)\s*min/i;

// Formats English date string to YYYY-MM-DD
const formatDate = (str) => {
    const date = new Date(str);
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    return `${year}-${month}-${day}`;
}

const parseWork = () => {
    const wrapper = $('div.video-detail')
    const video = wrapper.find('video')
    const info = wrapper.find('div.info')
    const texts = []
    info.contents().each(function () {
        if (this.nodeType === Node.TEXT_NODE) {
            const text = this.nodeValue.trim();
            if (text) {
                texts.push(text)
            }
        }
    });
    const match = texts[1].match(durationRegex);
    if (!match) {
        alert('无法匹配视频时长')
        throw 'Unmatched duration';
    }
    const duration = parseInt(match[1], 10) * 60;

    return {
        'title': wrapper.find('h1').text().trim(),
        'cover2': video.attr('poster'),
        'duration': duration,
        'releaseDate': formatDate(texts[2]),
        'producer': 'Virtual Taboo',
        'description': $('meta[name="twitter:description"]').attr('content'),
        'trailer': video.attr('src'),
        'source': window.location.href,
        'actors': info.find('a').map((i, ele) => $(ele).text()).get(),
        'genres': wrapper.find('div.tag-list a').map((i, ele) => $(ele).text()).get(),
        'images': wrapper.find('div.gallery-item-container a').map((i, ele) => $(ele).attr('href')).get().slice(0, -1),
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
    const btn = $('<div class="btn btn-full mt-5" style="background-color: orange">导出</div>');
    btn.on('click', () => exportWork());
    $('.right-info').prepend(btn);
})
