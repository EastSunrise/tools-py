// ==UserScript==
// @name         HuiAV Plugin
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Export resources into database
// @author       Kingen
// @require      https://cdn.staticfile.org/jquery/3.4.1/jquery.min.js
// @require      https://cdnjs.cloudflare.com/ajax/libs/layer/3.5.1/layer.js
// @match        https://www.huiav.com/*/
// ==/UserScript==

const getSerialNumber = () => {
    return $('.site a:last').text().trim()
}

const getOnlineLinks = () => {
    let links = []
    for (let ul of $('.list_box:first ul')) {
        links.push({
            'title': $(ul).find('.title:first').text().trim().replace('\n', ' '),
            'url': new URL($(ul).find('a:first').attr('href').replace('\n', ''), window.location),
            'time': $(ul).find('.time:first').text().trim()
        })
    }
    return links
}

const parseFilesize = (intro) => {
    intro = intro.toUpperCase()
    let introRegexp = /文件大小：\s*-?((\d+[,\s])?\d+(\.\.?\d*)?)\s?(KB|MB|GB|GIB)/
    let match = introRegexp.exec(intro)
    if (!match) {
        return intro
    }
    let filesize = Number(match[1].replace(',', '').replace(' ', '').replace('..', '.'))
    let unit = match[4]
    if ('GB' === unit || 'GIB' === unit) {
        filesize *= 1024 * 1024
    } else if ('MB' === unit) {
        filesize *= 1024
    }
    filesize *= 1024
    return Math.round(filesize)
}

const getMagnetLinks = () => {
    let links = []
    for (let ul of $('#magnet ul')) {
        links.push({
            'title': $(ul).find('.title:first').text().trim().replace('\n', ' '),
            'url': $(ul).find('span:first').text().trim().replace('\n', ' '),
            'filesize': parseFilesize($(ul).find('.intro:first').text().trim().replace('\n', ' '))
        })
    }
    return links
}

const retry = (fn, maxRetries, delay) => {
    return new Promise((resolve, reject) => {
        fn().then((result) => resolve(result))
            .catch((error) => {
                if (maxRetries <= 0) {
                    reject(error);
                } else {
                    setTimeout(() => retry(fn, maxRetries - 1, delay).then(resolve).catch(reject), delay);
                }
            });
    });
}

const getResources = () => {
    return new Promise((resolve, reject) => {
        let links = [].concat(getOnlineLinks(), getMagnetLinks());
        if (links.length > 0) {
            resolve([window.location.href].concat(links))
        } else {
            reject('no resources')
        }
    })
}

const exportResources = (resources) => {
    let sn = getSerialNumber()
    fetch('http://127.0.0.1:12301/study/work/' + sn + '/resource/import', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(resources)
    }).then(response => response.json()).then(result => {
        if (result.code === 0) {
            if (result.data > 0) {
                alert('成功' + result.data + '条资源');
            }
        } else {
            alert(result.message)
        }
    }).catch(reason => {
        alert(reason)
    })
}

$(function () {
    retry(getResources, 10, 3000)
        .then(resources => exportResources(resources))
        .catch(reason => alert(reason))
})
