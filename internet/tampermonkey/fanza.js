// ==UserScript==
// @name         Fanza Plugin
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Export work into database
// @author       Kingen
// @require      https://cdn.staticfile.org/jquery/3.4.1/jquery.min.js
// @require      https://cdnjs.cloudflare.com/ajax/libs/layer/3.5.1/layer.js
// @match        https://www.dmm.co.jp/mono/dvd/-/detail/=/cid=**
// @match        https://www.dmm.co.jp/digital/videoa/-/detail/=/cid=**
// ==/UserScript==

const api = '/study/api/v1';
const snRegex = /([a-z]{2,6})(\d{3,5})/g;
const samplePlayRegex = /sampleplay\('(\/digital\/[^']+)'\)/
const trailerRegex = /"src":\s*"([^"]+)"/;
const trailerRegex2 = /sampleUrl\s*=\s*"([^"]+)"/;

const goodType =
    window.location.href.match(/dmm\.co\.jp\/mono\/dvd\/*/) ? 'dvd' :
        window.location.href.match(/dmm\.co\.jp\/digital\/videoa\/*/) ? 'video' : 'unknown';

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

const parseDescription = () => {
    if (goodType === 'dvd') {
        return $('p.mg-b20').text().trim()
    }
    if (goodType === 'video') {
        return $('meta[name="description"]').attr('content').trim();
    }
    return null;
}

const parseDetail = () => {
    let info = {}
    for (let tr of $('table.mg-b20').find('tr')) {
        if ($(tr).find('td').length <= 1) {
            continue
        }
        let key = $(tr).find('td:eq(0)').text().trim();
        info[key] = $(tr).find('td:eq(1)');
    }
    return {
        'title': $('h1#title').text().trim(),
        'serialNumber': formatSn(info['品番：'].text().trim()),
        'duration': info['収録時間：'].text().trim().trim(),
        'releaseDate': (info['発売日：'] || info['商品発売日：']).text().trim().replace(/\//g, "-"),
        'producer': info['メーカー：'].text().trim(),
        'description': parseDescription(),
        'source': window.location.href,
        'actors': info['出演者：'].find('a').map((i, e) => $(e).text().trim()).toArray(),
        'directors': info['監督：'].find('a').map((i, e) => $(e).text().trim()).toArray(),
        'genres': info['ジャンル：'].find('a').map((i, e) => $(e).text().trim()).toArray(),
        'series': info['シリーズ：'].find('a').map((i, e) => $(e).text().trim()).toArray(),
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

const parseImages = () => {
    if (goodType === 'dvd') {
        const cover = $('#package-modal-image1 img').attr('src')
        const cover2 = $('meta[property="og:image"]').attr('content');
        const images = []
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

    if (goodType === 'video') {
        const cover = $('meta[property="og:image"]').attr('content');
        const cover2 = $('a[name="package-image"]').attr('href');
        const images = []
        for (let a of $('#sample-image-block').find('a')) {
            images.push($(a).attr('href'));
        }
        return {
            'cover': cover,
            'cover2': cover2,
            'images': images
        };
    }
    return {}
}

const getVideoTrailer = async (url) => {
    const frame = await $.get(url);
    const src = $(frame).attr('src');
    const data = await $.get(src);
    const match = trailerRegex.exec(data);
    if (match && match[1]) {
        return new URL(match[1], window.location.href).href;
    }
    console.log('data', data)
    alert('无法匹配视频预告片');
    return false;
}

const parseTrailer = async () => {
    if (goodType === 'dvd') {
        const url = $('#detail-sample-movie a').data('video-url');
        return await getVideoTrailer(url);
    }

    if (goodType === 'video') {
        let btn = $('#detail-sample-movie a');
        if (btn && btn.length > 0) {
            const url = samplePlayRegex.exec(btn.attr('onclick'))[1];
            return await getVideoTrailer(url);
        }

        btn = $('#detail-sample-vr-movie a');
        if (!btn || btn.length === 0) {
            alert('没有预告片')
            return false;
        }
        const src = samplePlayRegex.exec(btn.attr('onclick'))[1];
        const data = await $.get(src);
        const match = trailerRegex2.exec(data);
        if (match && match[1]) {
            return new URL(match[1], window.location.href).href;
        }
        console.log('data', data)
        alert('无法匹配VR预告片');
        return false;
    }

    alert('获取预告片失败：未知类型');
    return false;
}

const doPutWork = work => {
    console.log('save work', work);
    fetch(`${api}/works/${work['serialNumber']}?merge=1`, {
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
                    alert(`${text}：${result['serialNumber']}`);
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

const exportWork = (withDetail = false, withImages = false, withTrailer = false) => {
    if (!withDetail && !withImages && !withTrailer) {
        return
    }
    let work = {};
    let detail = parseDetail();
    if (withDetail) {
        work = detail;
    } else {
        work = {
            'title': detail['serialNumber'],
            'serialNumber': detail['serialNumber']
        }
    }
    if (withImages) {
        work = {...work, ...parseImages()};
    }
    work['source'] = window.location.href;
    if (withTrailer) {
        parseTrailer().then(trailer => {
            if (trailer) {
                work['trailer'] = trailer;
                doPutWork(work);
            } else {
                doPutWork(work);
            }
        });
    } else {
        doPutWork(work);
    }
}

$(function () {
    const btn = $('<button type="button" style="margin-left: 30px; float: right; background-color: orange">导出</button>');
    btn.on('click', () => exportWork(true, true, true));
    const btn2 = $('<button type="button" style="margin-left: 30px; float: right; background-color: orange">导出媒体</button>');
    btn2.on('click', () => exportWork(false, true, true));
    const btn3 = $('<button type="button" style="margin-left: 30px; float: right; background-color: orange">导出视频</button>');
    btn3.on('click', () => exportWork(false, false, true));
    $('#title').parent().append(btn, btn2, btn3);
})
