CREATE TABLE IF NOT EXISTS movies
(
    id             INTEGER NOT NULL
        primary key,
    title          TEXT    NOT NULL,
    alt            TEXT    NOT NULL,
    status         TEXT    NOT NULL, -- wish/do/collect
    tag_date       TEXT    NOT NULL, -- last date updating the status
    original_title TEXT,
    aka            list,
    subtype        TEXT    NOT NULL,
    languages      list    NOT NULL,
    year           INTEGER NOT NULL,
    durations      list    NOT NULL,
    current_season INTEGER,
    episodes_count INTEGER,
    seasons_count  INTEGER,
    archived       INTEGER NOT NULL, -- 0: unarchived, 1: archived, 2: downloading, 3: temp, 4: fail to download, 5:
    -- no resources
    location       TEXT,
    source         TEXT,
    last_update    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS resources
(
    id          INTEGER NOT NULL
        PRIMARY KEY AUTOINCREMENT,
    movie_id    INTEGER NOT NULL,
    protocol    TEXT    NOT NULL, -- http/ftp/pan/ed2k/magnet/unknown
    url         TEXT    NOT NULL,
    filename    TEXT,
    ext         TEXT,             -- file extension
    size        INTEGER,
    status      INTEGER NOT NULL, -- status of downloading. 0: to_add, 1: downloading, 2: abandoned, 3: done, negative: error_code
    msg         TEXT,
    source      TEXT,             -- source website
    remark      TEXT,
    last_update TEXT    NOT NULL
);

-- unique url
create unique index resources_url_uindex
    on resources (url, source);
