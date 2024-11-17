// ==UserScript==
// @name         Export Work
// @namespace    http://tampermonkey.net/
// @version      0.0.2
// @description  Export work into database
// @author       Kingen
// @require      https://cdn.staticfile.org/jquery/3.4.1/jquery.min.js
// @match        https://movie.douban.com/subject/*
// @match        https://www.dmm.co.jp/mono/dvd/-/detail/=/cid=*
// @match        https://www.dmm.co.jp/digital/videoa/-/detail/=/cid=*
// @match        https://www.straplez.com/model/*/movie/*
// @match        https://www.metartx.com/model/*/movie/*
// @match        https://nubilefilms.com/video/watch/*
// @match        https://www.teendreams.com/t4/*
// @match        https://virtualtaboo.com/videos/*
// @match        https://www.vixen.com/videos/*
// @match        https://www.vixen.com/performers/*
// @match        https://www.watch4beauty.com/updates/*
// @match        https://www.x-art.com/videos/*
// @match        https://www.wowgirlsblog.com/*
// @match        https://venus.allfinegirls.com/girl/*
// @match        https://venus.wowgirls.com/girl/*
// @match        https://cum4k.com/video/*
// @match        https://passion-hd.com/video/*
// @match        https://www.iafd.com/title.rme/id=*
// @match        https://www.kellymadison.com/models/*
// @match        https://www.twistys.com/scene/*
// @match        https://www.stripzvr.com/*
// ==/UserScript==

const root = 'https://127.0.0.1';
const rootApi = root + '/study/api/v1';

/**
 * Does the PUT request to save work to database
 */
const doPutWork = work => {
    if (!work) {
        return;
    }
    console.log('save work', work);
    fetch(`${rootApi}/works/none?merge=1`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(work)
    }).then(response => {
        if (response.status === 200 || response.status === 201) {
            const text = response.status === 200 ? 'Updated' : 'Created';
            response.json().then(
                result => {
                    console.log('success', result);
                    alert(`${text}: ${result['id']}`);
                }
            )
        } else if (response.status === 204) {
            alert('Ignored')
        } else if (response.status === 409) {
            response.json().then(
                result => {
                    console.log('conflict', result['data']);
                    const conflicts = []
                    result['data'].forEach(obj => conflicts.push(obj['field']));
                    const msg = `Conflicts: ${conflicts.join(', ')}.\nWant to retry without conflicts?`
                    if (confirm(msg)) {
                        conflicts.forEach(key => delete work[key]);
                        doPutWork(work);
                    }
                }
            )
        } else {
            response.text().then(text => {
                console.log('failed to save', text);
                alert('Failure: ' + text);
            })
        }
    }).catch(reason => {
        console.log('exception to save', reason);
        alert(reason)
    })
}

/**
 * Formats English date string to YYYY-MM-DD
 */
const formatDate = str => {
    const date = new Date(str);
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    return `${year}-${month}-${day}`;
}

const formatURL = url => {
    return new URL(url, window.location.href).href
}

const executeAfterLoad = (test, supply, timeout = 5000) => {
    return new Promise((resolve, reject) => {
        let count = timeout / 500;
        const timer = setInterval(() => {
            if (test()) {
                clearInterval(timer);
                console.log('Timer done.')
                resolve(supply())
            } else if (count <= 0) {
                clearInterval(timer);
                console.log('Timer timeout.')
                reject()
            } else {
                count--;
                console.log(`Timer ${count}...`)
            }
        }, 500);
    })
}

$(function () {
    const host = window.location.hostname;

    if (host === 'movie.douban.com') {
        const btn = $('<span style="margin-left: 30px; color: orange; cursor: pointer">导出</span>');
        $('#content h1').append(btn);
        btn.on('click', () => doPutWork(parseDoubanWork()));
    }

    if (host === 'www.dmm.co.jp') {
        const btn = $('<div class="sub-nav"><a href="javascript:void(0)">导出</a></div>');
        const goodType = window.location.pathname.startsWith('/mono/dvd') ? 'dvd' : 'video';
        if (goodType === 'dvd') {
            $('#mono-localnav').append(btn);
        } else {
            $('#digital-localnav').append(btn);
        }
        btn.on('click', async () => doPutWork(await parseFanzaWork(goodType)));
    }

    if (host === 'www.straplez.com' || host === 'www.metartx.com') {
        const btn = $('<div class="btn btn-primary join-btn" style="position: fixed; right: 50px">Export</div>');
        $('.navbar .va-m > div').append(btn);
        btn.on('click', async () => doPutWork(await parseMetArtWork()));
    }

    if (host === 'nubilefilms.com') {
        const btn = $('<li class="nav-item" style="margin-right: 20px"><span class="btn btn-cta btn-sm w-100 w-md-auto" style="cursor: pointer">Export</span></li>');
        $('.nav-right').prepend(btn);
        btn.on('click', () => doPutWork(parseNubileFilmsWork()));
    }

    if (host === 'www.teendreams.com') {
        const btn = $('<li><button style="color: orange">Export</button></li>');
        $('#social-tabs > ul').append(btn);
        btn.on('click', () => doPutWork(parseTeenDreamsWork()));
    }

    if (host === 'virtualtaboo.com') {
        const btn = $('<li><span class="btn btn-bold btn-green btn-join">Export</span></li>');
        $('.pull-right .nav:last').append(btn);
        btn.on('click', () => doPutWork(parseVirtualTabooWork()));
    }

    if (host === 'www.vixen.com') {
        if (window.location.pathname.startsWith('/videos/')) {
            const btn = $('<button id="export-btn" style="margin-left: 10px;">Export</button>');
            $('nav').append(btn);
            $('#export-btn').attr('class', $('#export-btn').prev().attr('class'))
            btn.on('click', () => doPutWork(parseVixenWork()));
        } else if (window.location.pathname.startsWith('/performers/')) {
            setInterval(() => {
                $('div.Grid__Item-f0cb34-1').each((i, ele) => {
                    if ($(ele).find('#my-export').length === 0) {
                        const btn = $('<button id="my-export" style="position: absolute; top: 10px; right: 10px; color: orange; z-index: 9999; cursor: pointer">Export</button>');
                        $(ele).append(btn);
                        btn.on('click', () => doPutWork(parseVixenWork($(ele))));
                    }
                })
            }, 500)
        }
    }

    if (host === 'www.watch4beauty.com') {
        executeAfterLoad(
            () => $('.third .top-menu-centered:first').length > 0,
            () => {
                const btn = $('<div class="top-menu-item"><a href="javascript:void(0)" style="font-weight: bolder">Export</a></div>');
                $('.third .top-menu-centered:first').append(btn);
                btn.on('click', async () => doPutWork(await parseWatch4BeautyWork()));
            }, 10000
        ).then(_ => _)
    }

    if (host === 'www.x-art.com') {
        const btn = $('<li><button style="background-color: #fd01f1; margin-left: 20px">Export</button></li>');
        $('.show-for-large-up.middle-menu').append(btn);
        btn.on('click', () => doPutWork(parseXArtWork()));
    }

    if (host === 'www.wowgirlsblog.com') {
        const btn = $('<button style="position: fixed; top: 50px; right: 5px;">Export</button>');
        $('#page').append(btn);
        btn.on('click', () => doPutWork(parseWowGirlsWork()));
    }

    if (host === 'venus.allfinegirls.com' || host === 'venus.wowgirls.com') {
        setInterval(() => {
            $('.cf_content_list div').each((i, ele) => {
                if ($(ele).find('#my-export').length === 0 && $(ele).find('.preview').length > 0) {
                    const btn = $('<button id="my-export" style="position: absolute; top: 10px; right: 10px; color: orange; z-index: 9999">Export</button>');
                    $(ele).append(btn);
                    btn.on('click', () => doPutWork(parseWowNetworkWork($(ele))));
                }
            })
        }, 500)
    }

    if (host === 'cum4k.com' || host === 'passion-hd.com') {
        const btn = $('<button class="btn cta" style="position: fixed; top: 18px; right: 50px; z-index: 9999">Export</button>');
        $('body').append(btn);
        btn.on('click', () => doPutWork(parseWhaleWork()));
    }

    if (host === 'www.iafd.com') {
        $('#topadzone').remove();
        const btn = $('<button class="btn btn-default" style="position: fixed; top: 8px; right: 20px; z-index: 9999">Export</button>');
        $('body').append(btn);
        btn.on('click', () => doPutWork(parseIafdWork()));
    }

    if (host === 'www.kellymadison.com') {
        setInterval(() => {
            $('div.card.episode').each((i, ele) => {
                if ($(ele).find('#my-export').length === 0) {
                    const btn = $('<button id="my-export" style="position: absolute; top: 10px; left: 10px; color: orange; z-index: 9999; cursor: pointer">Export</button>');
                    $(ele).append(btn);
                    btn.on('click', () => doPutWork(parseKellyMadisonWork($(ele))));
                }
            })
        }, 500)
    }

    if (host === 'www.twistys.com') {
        executeAfterLoad(
            () => $('nav [href="/joinf"]').length > 0,
            () => {
                const joinBtn = $('nav [href="/joinf"]').parent();
                const exportBtn = joinBtn.clone();
                exportBtn.remove('id');
                exportBtn.find('a').attr('href', 'javascript:void(0)');
                exportBtn.find('a').text('Export');
                joinBtn.parent().parent().append(exportBtn);
                exportBtn.on('click', () => doPutWork(parseTwistysWork()));
            }, 10000
        ).then(_ => _);
    }

    if (host === 'www.stripzvr.com' && window.location.pathname.split('/').length > 3) {
        $('.elementor-inner-section .elementor-container').each((i, section) => {
            const btn = $(section).find('.elementor-column:last').clone()
            btn.find('a').attr('href', 'javascript:void(0)');
            btn.find('a').text('Export')
            $(section).append(btn);
            btn.on('click', () => doPutWork(parseStripzvrWork()));
        })
    }
})

const parseDoubanWork = () => {
    const script = $('script[type="application/ld+json"]')
    const info = JSON.parse(script.text().replace(/\n/g, ''))
    return {
        'title': $('title').text().trim().slice(0, -5),
        'cover': info['image'].replace('s_ratio_poster', 'raw').replace('.webp', '.jpg'),
        'cover2': null,
        'duration': info['duration'],
        'releaseDate': info['datePublished'],
        'producer': null,
        'description': $('span[property="v:summary"]').text().trim().replace(/\n\s+/g, '\n'),
        'images': null,
        'trailer': null,
        'source': 'https://movie.douban.com' + info['url'],
        'actors': $('meta[property="video:actor"]').map((i, ele) => $(ele).attr('content').trim()).get(),
        'directors': $('meta[property="video:director"]').map((i, ele) => $(ele).attr('content').trim()).get(),
        'genres': info['genre'],
        'series': null
    }
}


const parseFanzaWork = async goodType => {
    const formatSn = sn => {
        const match = sn.match(/^\d{0,3}([a-z]{2,6})(\d{3,5})$/i);
        if (!match) {
            const input = prompt('Cannot format serial number. Please input manually.', sn.toUpperCase());
            if (input === null || input === '') {
                alert('Cannot format serial number. Cancelled!');
                return false;
            }
            return input;
        }
        const num = parseInt(match[2]);
        return match[1].toUpperCase() + '-' + String(num).padStart(3, '0');
    }

    const previewImage = src => {
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
            const images = $('.fn-sampleImage li.fn-sampleImage__zoom img')
                .map((i, ele) => previewImage($(ele).data('lazy') || $(ele).attr('src'))).get();
            return {
                'cover': $('#package-modal-image1 img').attr('src'),
                'cover2': $('meta[property="og:image"]').attr('content'),
                'images': images
            };
        }
        if (goodType === 'video') {
            return {
                'cover': $('meta[property="og:image"]').attr('content'),
                'cover2': $('a[name="package-image"]').attr('href'),
                'images': $('#sample-image-block a').map((i, ele) => $(ele).attr('href')).get()
            };
        }
        return {}
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

    const fetchVideoTrailer = async url => {
        const frame = await $.get(url);
        const src = $(frame).attr('src');
        const data = await $.get(src);
        const match = data.match(/"src":\s*"([^"]+)"/);
        return new URL(match[1], window.location.href).href;
    }

    const parseTrailer = async () => {
        if (goodType === 'dvd') {
            const url = $('#detail-sample-movie a').data('video-url');
            return await fetchVideoTrailer(url);
        }
        if (goodType === 'video') {
            const samplePlayRegex = /sampleplay\('(\/digital\/[^']+)'\)/
            const simpleBtn = $('#detail-sample-movie a');
            if (simpleBtn.length > 0) {
                const url = simpleBtn.attr('onclick').match(samplePlayRegex)[1];
                return await fetchVideoTrailer(url);
            }

            const vrBtn = $('#detail-sample-vr-movie a');
            if (vrBtn.length === 0) {
                alert('There is no trailer')
                return null;
            }
            const src = vrBtn.attr('onclick').match(samplePlayRegex)[1];
            const data = await $.get(src);
            const match = data.match(/sampleUrl\s*=\s*"([^"]+)"/);
            return new URL(match[1], window.location.href).href;
        }
        return null;
    }

    const info = {}
    for (let tr of $('table.mg-b20').find('tr')) {
        if ($(tr).find('td').length <= 1) {
            continue
        }
        let key = $(tr).find('td:eq(0)').text().trim();
        info[key] = $(tr).find('td:eq(1)');
    }

    const serialNumber = formatSn(info['品番：'].text().trim());
    if (!serialNumber) {
        return false;
    }

    return {
        'title': $('h1#title').text().trim(),
        'serialNumber': serialNumber,
        'duration': info['収録時間：'].text().trim(),
        'releaseDate': (info['発売日：'] || info['商品発売日：']).text().trim().replace(/\//g, "-"),
        'producer': info['メーカー：'].text().trim(),
        'description': parseDescription(),
        'trailer': await parseTrailer(),
        'source': window.location.href,
        'actors': info['出演者：'].find('a').map((i, ele) => $(ele).text().trim()).get(),
        'directors': info['監督：'].find('a').map((i, ele) => $(ele).text().trim()).get(),
        'genres': info['ジャンル：'].find('a').map((i, ele) => $(ele).text().trim()).get(),
        'series': info['シリーズ：'].find('a').map((i, ele) => $(ele).text().trim()).toArray(),
        ...parseImages()
    }
}


const parseMetArtWork = async () => {
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
        const matches = $('div.jw-preview').attr('style').match(/url\((&quot;|")(.*?)(&quot;|")\);/);
        if (matches && matches[2]) {
            cover2 = matches[2];
        } else {
            alert('Cannot get cover!')
            return false;
        }
    }

    document.querySelector('a.clickable').click()
    const description = await executeAfterLoad(
        () => $('a.clickable').text().trim() === 'Hide',
        () => $('a.clickable').prev().text().trim()
    )

    return {
        'title': $('ol.container li:last').text().trim(),
        'cover': $('.movie-details .panel-content img').attr('src'),
        'cover2': cover2,
        'duration': parseInt($('meta[property="og:video:duration"]').attr('content')),
        'releaseDate': formatDate(info['Released:'].text().trim()),
        'producer': $('.logo img').attr('alt'),
        'description': description,
        'images': null,
        'trailer': null,
        'source': window.location.href,
        'actors': info['Cast:'].find('a').map((i, ele) => $(ele).text().trim()).get(),
        'directors': info['Director:'].find('a').map((i, ele) => $(ele).text().trim()).get(),
        'genres': $('meta[property="og:video:tag"]').map((i, ele) => $(ele).attr('content')).get(),
        'series': null
    }
}


const parseNubileFilmsWork = () => {
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


const parseTeenDreamsWork = () => {
    const script = $('.innerOld > script').text()
    return {
        'title': $('meta[property="og:title"]').attr('content').trim(),
        'cover': null,
        'cover2': formatURL(script.match(/poster="([^"]*)"/)[1].replace('-1x.', '-4x.')),
        'duration': $('.player-time').text().split('/')[1].trim(),
        'releaseDate': $('.content-date').text().trim().split(':')[1].trim(),
        'producer': 'TeenDreams',
        'description': null,
        'images': null,
        'trailer': formatURL(script.match(/src="([^"]*)"/)[1]),
        'source': window.location.href,
        'actors': $('.item-name').text().trim(),
        'directors': null,
        'genres': null,
        'series': null
    }
}


const parseVirtualTabooWork = () => {
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
    const match = texts[1].match(/(\d+)\s*min/i);
    const duration = parseInt(match[1], 10) * 60;

    return {
        'title': wrapper.find('h1').text().trim(),
        'cover': null,
        'cover2': video.attr('poster'),
        'duration': duration,
        'releaseDate': formatDate(texts[2]),
        'producer': 'Virtual Taboo',
        'description': $('meta[name="twitter:description"]').attr('content'),
        'images': wrapper.find('div.gallery-item-container a').map((i, ele) => $(ele).attr('href')).get().slice(0, -1),
        'trailer': video.attr('src'),
        'source': window.location.href,
        'actors': info.find('a').map((i, ele) => $(ele).text()).get(),
        'directors': null,
        'genres': wrapper.find('div.tag-list a').map((i, ele) => $(ele).text()).get(),
        'series': null
    }
}


const parseVixenWork = card => {
    if (!card) { // the whole page
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
    } else { // the card
        return {
            'title': $(card).find('a[data-test-component="TitleLink"]').text().trim(),
            'cover': null,
            'cover2': $(card).find('picture img').attr('src'),
            'duration': null,
            'releaseDate': formatDate($(card).find('div[data-test-component="ReleaseDateFormatted"]').text().trim()),
            'producer': 'VIXEN',
            'description': null,
            'images': null,
            'trailer': $(card).find('video').attr('src'),
            'source': window.location.href,
            'actors': $(card).find('div[data-test-component="Models"] a').map((i, ele) => $(ele).text().trim()).get(),
            'directors': null,
            'genres': null,
            'series': null
        }
    }
}


const parseWatch4BeautyWork = async () => {
    $('#action-item-05').click();
    return await executeAfterLoad(
        () => $('#lightbox-info').length > 0,
        () => {
            const cover = $('#gallcover .loadable-data img').attr('src')
            const dateMatch = $('.issue-detail > .link').text().trim().match(/Published (\d{4})\.(\d{1,2})\.(\d{1,2})/);
            const year = dateMatch[1];
            const month = dateMatch[2].padStart(2, '0');
            const day = dateMatch[3].padStart(2, '0');
            const durationMatch = $('.issue-detail .hero:first').text().trim().match(/((\d{1,2}:)?\d{1,2}:\d{1,2}) FILM/)

            return {
                'title': document.title.substring(5),
                'cover': cover.includes('wide') ? cover.replace('cover-wide-2560.', 'cover-960.') : cover,
                'cover2': cover.includes('wide') ? cover : $('video').attr('poster'),
                'duration': durationMatch ? durationMatch[1] : null,
                'releaseDate': `${year}-${month}-${day}`,
                'producer': 'Watch4beauty',
                'description': $('.gentext p').text().trim(),
                'images': $('.photos.grid .loadable-data img').map((i, ele) => formatURL($(ele).attr('src'))).get(),
                'trailer': null,
                'source': window.location.href,
                'actors': $('#lightbox-info p:eq(2) a').map((i, ele) => $(ele).text().trim()).get(),
                'directors': null,
                'genres': $('a.tag').map((i, ele) => $(ele).text().trim()).get(),
                'series': null
            }
        }
    )
}


const parseXArtWork = () => {
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


const parseWowGirlsWork = () => {
    const info = JSON.parse($('.flowplayer').attr('data-item'))
    return {
        'title': $('meta[itemprop="name"]').attr('content'),
        'cover': null,
        'cover2': $('meta[property="og:image"]').attr('content'),
        'duration': $('meta[itemprop="duration"]').attr('content'),
        'releaseDate': $('meta[itemprop="uploadDate"]').attr('content').split('T')[0],
        'producer': 'WowGirls',
        'description': null,
        'images': null,
        'trailer': info['sources'][0]['src'],
        'source': window.location.href,
        'actors': $('#video-actors a').map((i, ele) => $(ele).text().trim()).get(),
        'directors': null,
        'genres': null,
        'series': null
    }
}


const parseWowNetworkWork = card => {
    return {
        'title': $(card).find('a.title').text().trim(),
        'cover': null,
        'cover2': $(card).find('.thumb img').attr('src'),
        'duration': null,
        'releaseDate': null,
        'producer': null,
        'description': null,
        'images': null,
        'trailer': null,
        'source': [window.location.href, formatURL($(card).find('a.title').attr('href'))],
        'actors': $(card).find('.models a').map((i, ele) => $(ele).text().trim()).get(),
        'directors': null,
        'genres': $(card).find('.genres a').map((i, ele) => $(ele).text().trim()).get(),
        'series': null
    };
}


const parseWhaleWork = () => {
    return {
        'title': $('h1.leading-tight').text().trim(),
        'cover': null,
        'cover2': $('#player').attr('poster').split('?')[0],
        'duration': null,
        'releaseDate': null,
        'producer': $('.logo:first').attr('alt'),
        'description': $('div.items-start').text().trim(),
        'images': $('main div.hidden.flex-row img').map((i, ele) => $(ele).attr('src').split('?')[0]).get(),
        'trailer': $('#player source').attr('src'),
        'source': window.location.href,
        'actors': $('.scene-info .link-list-with-commas a').map((i, ele) => $(ele).text().trim()).get(),
        'directors': null,
        'genres': null,
        'series': null
    }
}


const parseIafdWork = () => {
    const headers = $('p.bioheading').map((i, ele) => $(ele).text().trim()).get()
    const values = $('p.biodata').map((i, ele) => $(ele).text().trim()).get()
    const info = Object.fromEntries(headers.map((header, i) => [header, values[i]]));
    return {
        'title': $('.container h1').text().trim().match(/^(.+)\(\d{4}\)$/)[1].trim(),
        'cover': null,
        'cover2': null,
        'duration': parseInt(info['Minutes']) * 60,
        'releaseDate': formatDate(info['Release Date']),
        'producer': info['Studio'],
        'description': $('#synopsis .padded-panel li').map((i, ele) => $(ele).text().trim()).get().join('\n'),
        'images': null,
        'trailer': null,
        'source': window.location.href,
        'actors': $('.castbox a').map((i, ele) => $(ele).text().trim()).get(),
        'directors': null,
        'genres': null,
        'series': null
    }
}


const parseKellyMadisonWork = card => {
    const sn = $(card).find('.card-footer-item:last').text().trim()
    return {
        'title': $(card).find('p.title a').text().trim(),
        'cover': null,
        'cover2': $(card).find('.image img').attr('src'),
        'duration': null,
        'releaseDate': null,
        'producer': sn.startsWith('TF') ? 'TeenFidelity' : (sn.startsWith('PF') ? 'PornFidelity' : 'Unknown'),
        'description': null,
        'images': null,
        'trailer': $(card).find('video').attr('src'),
        'source': [window.location.href, formatURL($(card).find('p.title a').attr('href'))],
        'actors': $(card).find('.subtitle.is-7 a').map((i, ele) => $(ele).text().trim()).get(),
        'directors': null,
        'genres': null,
        'series': null
    };
}


const parseTwistysWork = () => {
    const info = JSON.parse($('script[type="application/ld+json"]').text().trim())
    return {
        'title': info['name'],
        'cover': null,
        'cover2': info['thumbnailUrl'],
        'duration': null,
        'releaseDate': info['uploadDate'],
        'producer': 'Twistys',
        'description': info['description'],
        'images': null,
        'trailer': info['contentUrl'],
        'source': window.location.href,
        'actors': $('h2.bUcZjY a').map((i, ele) => $(ele).text().trim()).get(),
        'directors': null,
        'genres': $('div.hBUrvM a').map((i, ele) => $(ele).text().trim()).get(),
        'series': null
    }
}


const parseStripzvrWork = () => {
    const data = JSON.parse($('script[type="application/ld+json"]').text().trim())
    const graphs = Object.fromEntries(data['@graph'].map(g => [g['@type'], g]))
    const webpage = graphs['WebPage']
    const imgRegex = /^background-image: url\('([^']+)'\)$/
    const images = $('.swiper-wrapper .swiper-slide:not(.swiper-slide-duplicate) .elementor-carousel-image')
        .map((i, ele) => $(ele).attr('style').match(imgRegex)[1]).get()

    return {
        'title': webpage['name'].split('featuring')[0].trim(),
        'cover': null,
        'cover2': webpage['thumbnailUrl'],
        'duration': null,
        'releaseDate': webpage['datePublished'].split('T')[0],
        'producer': 'StripzVR',
        'description': webpage['description'],
        'images': images,
        'trailer': $('#elementor-tab-content-8441 a:first').attr('href'),
        'source': window.location.href,
        'actors': $('.elementor-widget-text-editor a [style="color: #ff3399;"]').map((i, ele) => $(ele).text().trim()).get(),
        'directors': null,
        'genres': ['VR'],
        'series': null
    }
}