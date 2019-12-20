#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@Description 生成脚本
@Module generator

@Author Kingen
@Date 2019/8/27
@Version 1.0
"""
from tkinter import filedialog

import xlrd

from generator.mybatis.oracle import Database
from generator.util.utils import create_file


def create_tables_sql(database=Database.KXD) -> list:
    """
    解析数据表设计的Excel文件，生成对应的建表sql文件
    :param database: 默认为KXD
    :arg: sheet index
    :return: 建表sql列表
    """
    heads = {
        "field_name": "列名",
        "field_desc": "注释",
        "data_type": "类型",
        "is_null": "是否可空",
        "is_primary_key": "主键",
        "is_unique": "唯一索引",
        "is_index": "查询索引"
    }
    filename = filedialog.askopenfilename()
    if not filename:
        return []
    workbook = xlrd.open_workbook(filename)
    sql_tables = []
    for sheet_index, sheet in enumerate(workbook.sheets()):
        sheet_name = sheet.name
        if not sheet_name.startswith("T_"):
            continue
        if sheet.nrows < 2:
            continue
        table_name = database.name + "." + sheet_name
        sql_drop = "DROP TABLE " + table_name + ";"

        # read values
        values = {}
        for index in range(sheet.ncols):
            column = sheet.col_values(index)
            values[column[0]] = column

        sql_fields = []
        sql_comments = ["COMMENT ON TABLE " + table_name + " IS '';"]
        primary_keys = []
        unique_keys = []
        index_keys = []
        for index in range(1, sheet.nrows):
            field_name = values[heads["field_name"]][index]
            data_type = values[heads["data_type"]][index]

            field_parts = [field_name]
            if data_type.upper().find("CHAR") != -1:
                data_type = data_type.replace(')', 'BYTE)', 1)
            if data_type.upper() == "TIMESTAMP":
                data_type = "TIMESTAMP(0)"
            field_parts.append(data_type)
            field_parts.append("NOT NULL" if values[heads["is_null"]][index] == "N" else "NULL")
            sql_fields.append("\t" + " ".join(field_parts))

            sql_comments.append(
                "COMMENT ON COLUMN " + table_name + "." + field_name + " IS '" + values[heads["field_desc"]][
                    index] + "';")

            if values[heads["is_primary_key"]][index] == "Y":
                primary_keys.append(field_name)
            if values.get(heads["is_unique"], [])[index] == "Y":
                unique_keys.append(field_name)
            if values.get(heads["is_index"], [])[index] == "Y":
                index_keys.append(field_name)

        sql_create = "CREATE TABLE " + table_name + "(\n" + ",\n".join(sql_fields) + ");"
        sql_indexes = ["ALTER TABLE " + table_name + " ADD PRIMARY KEY (" + ("/* todo 请添加主键*/" if (
                len(primary_keys) == 0) else ",".join(primary_keys)) + ");"]
        if len(unique_keys) > 0:
            sql_indexes.append("ALTER TABLE " + table_name + " ADD UNIQUE (" + ",".join(unique_keys) + ");")
        if len(index_keys) > 0:
            for index_key in index_keys:
                sql_indexes.append(
                    "CREATE INDEX INDEX_" + sheet_name + "_" + index_key + "  ON " + table_name + "(" + index_key
                    + ");")

        sql_tables.append("\n".join([sql_drop, sql_create, "\n".join(sql_comments), "\n".join(sql_indexes)]))

    if len(sql_tables) == 0:
        return []
    sql_tables.append("COMMIT;")

    # write to file
    create_file('\n\n'.join(sql_tables), '/', '01_SYS_CREATE_TABLE.sql', False, encoding='UTF-8')
    return sql_tables


def create_tables_sql_mysql(filename, database=Database.lol) -> list:
    """
    解析数据表设计的Excel文件，生成对应的建表sql文件
    :param filename:
    :param database: 默认为KXD
    :arg: sheet index
    :return: 建表sql列表
    """
    heads = {
        "field_name": "列名",
        "field_desc": "注释",
        "data_type": "类型",
        "is_null": "是否可空",
        "is_primary_key": "主键",
        "is_unique": "唯一索引",
        "is_index": "查询索引",
        "is_auto_increment": "是否自增"
    }
    workbook = xlrd.open_workbook(filename)
    sql_tables = []
    for sheet_index, sheet in enumerate(workbook.sheets()):
        sheet_name = sheet.name.lower()
        if sheet_index < 1 or sheet.nrows < 2:
            continue
        table_name = database.name + "." + sheet_name
        sql_drop = 'drop table if exists {0};'.format(table_name)

        # read values
        values = {}
        for index in range(sheet.ncols):
            column = sheet.col_values(index)
            values[column[0]] = column

        sql_fields = []
        primary_keys = []
        for index in range(1, sheet.nrows):
            field_name = values[heads["field_name"]][index].lower()
            data_type = values[heads["data_type"]][index].lower()

            field_parts = [
                field_name,
                data_type,
                'auto_increment' if values[heads["is_auto_increment"]][index] == 'Y' else '',
                "not null" if values[heads["is_null"]][index] == "N" else "null",
                'comment \'' + values[heads["field_desc"]][index] + '\'']
            sql_fields.append("\t" + " ".join(field_parts))

            if values[heads["is_primary_key"]][index] == "Y":
                primary_keys.append(field_name)

        sql_fields.append('\tprimary key (' + primary_keys[0] + ')')
        sql_create = "create table " + table_name + "(\n" + ",\n".join(sql_fields) + "\n);"

        sql_tables.append("\n".join([sql_drop, sql_create]))

    if len(sql_tables) == 0:
        return []
    sql_tables.append("COMMIT;")

    # write to file
    sql_result = '\n\n'.join(sql_tables)
    print(sql_result)
    create_file(sql_result, 'D:/', '01_SYS_CREATE_TABLE.sql', False, encoding='UTF-8')
    return sql_tables


if __name__ == '__main__':
    create_tables_sql_mysql('D:/Docs/OneDrive/Development/03 LOL/03 开发设计/24 数据表设计.xlsx')
