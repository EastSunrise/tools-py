// ==UserScript==
// @name         Fanza Plugin
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Export work into database
// @author       Kingen
// @require      https://cdn.staticfile.org/jquery/3.4.1/jquery.min.js
// @require      https://cdnjs.cloudflare.com/ajax/libs/layer/3.5.1/layer.js
// @match        https://www.dmm.co.jp/mono/dvd/-/detail/=/cid=**
// ==/UserScript==

const snRegex = /([a-z]{2,6})(\d{3,5})/g;
const trailerRegex = /"src":\s*"([^"]+)"/;

const formatSn = sn => {
    let match = snRegex.exec(sn);
    if (!match || match[0] !== sn) {
        let input = prompt('格式化序列号失败，请输入', sn.toUpperCase());
        if (input === null || input === '') {
            alert('序列号格式化失败，已取消');
            throw '序列号格式化失败，已取消';
        }
        return input;
    }
    let num = parseInt(match[2]);
    return match[1].toUpperCase() + '-' + String(num).padStart(3, '0');
}

const getDetail = () => {
    let info = {}
    for (let tr of $('.wrapper-product table').find('tr')) {
        if ($(tr).find('td').length <= 1) {
            continue
        }
        let key = $(tr).find('td:eq(0)').text().trim();
        info[key] = $(tr).find('td:eq(1)');
    }
    return {
        'title': $('h1#title').text().trim(),
        'release_date': info['発売日：'].text().trim().replace(/\//g, "-"),
        'duration': info['収録時間：'].text().trim(),
        'actors': info['出演者：'].find('a').map((i, e) => $(e).text().trim()).toArray(),
        'director': info['監督：'].find('a').map((i, e) => $(e).text().trim()).toArray(),
        'series': info['シリーズ：'].find('a').map((i, e) => $(e).text().trim()).toArray(),
        'producer': info['メーカー：'].text().trim(),
        'genres': info['ジャンル：'].find('a').map((i, e) => $(e).text().trim()).toArray(),
        'serial_number': formatSn(info['品番：'].text().trim()),
        'description': $('p.mg-b20').text().trim()
    }
}

const previewSrc = (src) => {
    if (src.match(/(p[a-z]\.)jpg/)) {
        return src.replace(RegExp.$1, 'pl.');
    } else if (src.match(/store/)) {
        let path = src.split('/');
        let pid = path[path.length - 2];
        let reg = new RegExp(pid + '/' + pid + 'ts\-([0-9]+)\.jpg$');
        if (src.match(reg)) {
            return src.replace('ts-', 'tl-');
        } else {
            return src.replace('-', 'jp-');
        }
    } else if (src.match(/consumer_game/)) {
        return src.replace('js-', '-');
    } else if (src.match(/js-([0-9]+)\.jpg$/)) {
        return src.replace('js-', 'jp-');
    } else if (src.match(/ts-([0-9]+)\.jpg$/)) {
        return src.replace('ts-', 'tl-');
    } else if (src.match(/(-[0-9]+\.)jpg$/)) {
        return src.replace(RegExp.$1, 'jp' + RegExp.$1);
    } else {
        return src.replace('-', 'jp-');
    }
}

const resolveUrl = relativeUrl => {
    return new URL(relativeUrl, window.location.href).href;
}


const getTrailer = (callback) => {
    let url = $('.fn-sampleVideoBtn').data('video-url');
    $.get(url, frame => {
        let src = $(frame).attr('src');
        return $.get(src, data => {
            const match = trailerRegex.exec(data);
            if (match && match[1]) {
                callback(resolveUrl(match[1]));
            } else {
                alert('获取预告片失败');
            }
        });
    });
}


const getImages = () => {
    let cover = $('#package-modal-image1 img').attr('src')
    let cover2 = $('meta[property="og:image"]').attr('content');
    let images = []
    for (let img of $('.fn-sampleImage li.fn-sampleImage__zoom').find('img')) {
        let src = $(img).data('lazy') || $(img).attr('src');
        images.push(previewSrc(src));
    }
    return {
        'cover': cover,
        'cover2': cover2,
        'images': images
    };
}

const exportWork = work => {
    console.log(work);
    fetch('https://192.168.1.110/study/work/import', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(work)
    }).then(response => response.json()).then(result => {
        if (result.code === 0) {
            if (result['updated']) {
                alert('已更新');
            } else {
                alert('已忽略');
            }
        } else {
            alert(result.message);
            console.log(result['conflicts']);
        }
    }).catch(reason => {
        alert(reason)
    })
}

const exportAll = () => {
    getTrailer(trailer => {
        let work = {
            ...getDetail(),
            ...getImages(),
            'trailer': trailer,
            'source': window.location.href
        }
        exportWork(work);
    });
}

const exportTrailer = () => {
    getTrailer(trailer => {
        let sn = getDetail()['serial_number'];
        let work = {
            'serial_number': sn,
            'trailer': trailer,
            'source': window.location.href
        }
        exportWork(work);
    });
}

$(function () {
    const btn = $('<button style="margin-right: 0; background-color: orange">导出</button>');
    btn.on('click', exportAll);
    const btn2 = $('<button style="margin-right: 0; background-color: orange">导出视频</button>');
    btn2.on('click', exportTrailer);
    $('.box-rank').append(btn, btn2);
})
