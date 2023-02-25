#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Operations for pdf files.

@Author Kingen
"""
import os.path
from typing import Union, Optional

from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import Destination, IndirectObject, NullObject

import common

log = common.create_logger(__name__)


def self(x):
    return x


def update_bookmarks(filepath, title_func=self, page_func=self, **kwargs):
    reader = PdfReader(filepath)
    writer = PdfWriter()

    log.info("Copying pages")
    for page in reader.pages:
        writer.add_page(page)
    log.info("Copying metadata")
    writer.add_metadata(reader.metadata)

    log.info("Copying bookmarks")
    copy_bookmarks(reader, writer, reader.outline, title_func, page_func, parent=None, **kwargs)
    basename, ext = os.path.splitext(filepath)
    dst_path = basename + "（副本）" + ext
    log.info("Writing to %s", dst_path)
    writer.write(dst_path)


def copy_bookmarks(reader: PdfReader, writer: PdfWriter, bookmark: Union[Destination, list], title_func=self, page_func=self,
                   parent=None, color=None, bold=None, italic=None) -> Optional[IndirectObject]:
    if isinstance(bookmark, Destination):
        title = title_func(bookmark.title)
        page_num = page_func(reader.get_destination_page_number(bookmark))
        zoom = [bookmark.left, bookmark.top, bookmark.zoom]
        zoom = [None if isinstance(x, NullObject) else x for x in zoom]
        return writer.add_outline_item(title, page_num, parent, color, bold, italic, "/XYZ", *zoom)
    elif isinstance(bookmark, list):
        previous = None
        for child in bookmark:
            if isinstance(child, Destination):
                previous = copy_bookmarks(reader, writer, child, title_func, page_func, parent, color, bold, italic)
            elif isinstance(child, list):
                previous = copy_bookmarks(reader, writer, child, title_func, page_func, previous, color, bold, italic)
            else:
                raise ValueError()
        return None
    else:
        raise ValueError()
