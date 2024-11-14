// ==UserScript==
// @name         Export Work
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Export work into database
// @author       Kingen
// @require      https://cdn.staticfile.org/jquery/3.4.1/jquery.min.js
// @match        https://movie.douban.com/subject/**
// @match        https://www.straplez.com/model/*/movie/**
// @match        https://www.metartx.com/model/*/movie/**
// @match        https://nubilefilms.com/video/watch/**
// @match        https://www.teendreams.com/t4/**
// @match        https://virtualtaboo.com/videos/**
// @match        https://www.vixen.com/videos/**
// @match        https://www.watch4beauty.com/updates/**
// @match        https://www.x-art.com/videos/**
// @match        https://www.wowgirlsblog.com/**
// @match        https://venus.allfinegirls.com/girl/**
// @match        https://venus.wowgirls.com/girl/**
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
                    alert('Conflicts: ' + result['data'].map(obj => obj['field']).join(', '));
                }
            )
        } else {
            response.text().then(text => {
                console.log('failed to save', text);
                alert('Failure: ' + text);
            })
        }
    }).catch(reason => {
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

$(function () {
    const host = window.location.hostname;

    if (host === 'movie.douban.com') {
        const btn = $('<span style="margin-left: 30px; color: orange; cursor: pointer">导出</span>');
        $('#content h1').append(btn);
        btn.on('click', () => doPutWork(parseDoubanWork()));
    }

    if (host === 'www.straplez.com' || host === 'www.metartx.com') {
        const btn = $('<div class="btn btn-primary join-btn" style="position: fixed; right: 50px">导出</div>');
        $('.navbar .va-m > div').append(btn);
        btn.on('click', () => doPutWork(parseMetArtWork()));
    }

    if (host === 'nubilefilms.com') {
        const btn = $('<li class="nav-item" style="margin-right: 20px"><span class="btn btn-cta btn-sm w-100 w-md-auto" style="cursor: pointer">导出</span></li>');
        $('.nav-right').prepend(btn);
        btn.on('click', () => doPutWork(parseNubileFilmsWork()));
    }

    if (host === 'www.teendreams.com') {
        const btn = $('<li><button style="color: orange">导出</button></li>');
        $('#social-tabs > ul').append(btn);
        btn.on('click', () => doPutWork(parseTeenDreamsWork()));
    }

    if (host === 'virtualtaboo.com') {
        const btn = $('<li><span class="btn btn-bold btn-green btn-join">导出</span></li>');
        $('.pull-right .nav:last').append(btn);
        btn.on('click', () => doPutWork(parseVirtualTabooWork()));
    }

    if (host === 'www.vixen.com') {
        const btn = $('<button id="export-btn" style="margin-left: 10px;">导出</button>');
        $('nav').append(btn);
        $('#export-btn').attr('class', $('#export-btn').prev().attr('class'))
        btn.on('click', () => doPutWork(parseVixenWork()));
    }

    if (host === 'www.watch4beauty.com') {
        const timer = setInterval(() => {
            if ($('.third .top-menu-centered:first').length > 0) {
                clearInterval(timer);
                const btn = $('<div class="top-menu-item"><a href="javascript:void(0)" style="font-weight: bolder">导出</a></div>');
                $('.third .top-menu-centered:first').append(btn);
                btn.on('click', () => exportWatch4BeautyWork());
            }
        }, 500);
    }

    if (host === 'www.x-art.com') {
        const btn = $('<li><button style="background-color: #fd01f1; margin-left: 20px">导出</button></li>');
        $('.show-for-large-up.middle-menu').append(btn);
        btn.on('click', () => doPutWork(parseXArtWork()));
    }

    if (host === 'www.wowgirlsblog.com') {
        const btn = $('<button style="position: fixed; top: 50px; right: 5px;">导出</button>');
        $('#page').append(btn);
        btn.on('click', () => doPutWork(parseWowGirlsWork()));
    }

    if (host === 'venus.allfinegirls.com' || host === 'venus.wowgirls.com') {
        setInterval(() => {
            $('.cf_content_list div').each((i, ele) => {
                if ($(ele).find('#my-export').length === 0 && $(ele).find('.preview').length > 0) {
                    const btn = $('<button id="my-export" style="position: absolute; top: 10px; right: 10px; color: orange; z-index: 9999">导出</button>');
                    $(ele).append(btn);
                    btn.on('click', () => doPutWork(parseWowNetworkWork($(ele))));
                }
            })
        }, 500)
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


const parseMetArtWork = () => {
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
    if (!match) {
        alert('无法匹配视频时长')
        return false;
    }
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


const parseVixenWork = () => {
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


const exportWatch4BeautyWork = () => {
    $('#action-item-05').click();
    const timer = setInterval(() => {
        if ($('#lightbox-info').length > 0) {
            clearInterval(timer)
            console.log('已打开作品详情页')

            const cover = $('#gallcover .loadable-data img').attr('src')
            const dateMatch = $('.issue-detail > .link').text().trim().match(/Published (\d{4})\.(\d{1,2})\.(\d{1,2})/);
            const year = dateMatch[1];
            const month = dateMatch[2].padStart(2, '0');
            const day = dateMatch[3].padStart(2, '0');
            const durationMatch = $('.issue-detail .hero:first').text().trim().match(/((\d{1,2}:)?\d{1,2}:\d{1,2}) FILM/)

            doPutWork({
                'title': document.title.substring(5),
                'cover': cover.includes('wide') ? cover.replace('cover-wide-2560.', 'cover-960.') : cover,
                'cover2': cover.includes('wide') ? cover : $('video').attr('poster'),
                'duration': durationMatch ? durationMatch[1] : null,
                'releaseDate': `${year}-${month}-${day}`,
                'producer': 'Watch4beauty',
                'description': null,
                'images': null,
                'trailer': null,
                'source': window.location.href,
                'actors': $('#lightbox-info p:eq(2) a').map((i, ele) => $(ele).text().trim()).get(),
                'directors': null,
                'genres': $('a.tag').map((i, ele) => $(ele).text().trim()).get(),
                'series': null
            })
        }
    }, 500)
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


const parseWowNetworkWork = ele => {
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
    };
}