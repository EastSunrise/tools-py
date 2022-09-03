#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Generates SQL.

@Author Kingen
"""
import logging
import os.path
from enum import Enum
from tkinter import filedialog
from typing import List

import xlrd
from cx_Oracle import Connection

from dev.generator import JavaType
from dev.generator.template import QueryColumns


class TableDesigner:
    field_name = "列名",
    field_desc = "注释",
    data_type = "类型",
    is_null = "是否可空",
    is_primary_key = "主键",
    is_unique = "唯一索引",
    is_index = "查询索引",
    is_auto_increment = "是否自增"


def generate_table_creation(filepath: str, db_name: str) -> List[str]:
    """
    Reads a tables-design document to generate table creation statements.
    """
    if not os.path.isfile(filepath):
        filepath = filedialog.askopenfilename()
    if not filepath:
        raise ValueError("Please select a file")
    workbook = xlrd.open_workbook(filepath)
    sql_tables = []
    for sheet_index, sheet in enumerate(workbook.sheets()):
        sheet_name = sheet.name.lower()
        if sheet_index < 1 or sheet.nrows < 2:
            continue
        table_name = db_name + "." + sheet_name
        sql_drop = f"drop table if exists {table_name};"

        columns = [sheet.col_values(i) for i in range(sheet.ncols)]
        fields = dict([(col[0], col) for col in columns])

        sql_fields = []
        primary_keys = []
        for index in range(1, sheet.nrows):
            field_name = fields[TableDesigner.field_name][index].lower()

            field_parts = [
                field_name,
                fields[TableDesigner.data_type][index].lower(),
                'auto_increment' if fields[TableDesigner.is_auto_increment][index] == 'Y' else '',
                "not null" if fields[TableDesigner.is_null][index] == "N" else "null",
                'comment \'' + fields[TableDesigner.field_desc][index] + '\''
            ]
            sql_fields.append("\t" + " ".join(field_parts))

            if fields[TableDesigner.is_primary_key][index] == "Y":
                primary_keys.append(field_name)

        sql_fields.append('\tprimary key (' + primary_keys[0] + ')')
        sql_create = "create table " + table_name + "(\n" + ",\n".join(sql_fields) + "\n);"
        sql_tables.append("\n".join([sql_drop, sql_create]))
    return sql_tables


class OracleProxy:
    def __init__(self, conn: Connection):
        self.__conn = conn

    def select(self, table_name, result=None, parameter_dict=None, order_dict=None, num_rows=None) -> list:
        """
        单表查询
        :param table_name:
        :param result: 要获取的结果字段list：['ID', 'NAME']，或是映射dict：{'ID': 'id', 'NAME': 'username'}
        :param parameter_dict: 查询条件dict：{'id': '1234'}
        :param order_dict: 排序规则dict：{'NAME': 'DESC'}
        :param num_rows: 选取记录数，默认全部
        :return:
        """
        if not table_name:
            raise ValueError(f"表'{table_name}'不存在")
        if result is None:
            result = {}
        if order_dict is None:
            order_dict = {}
        if parameter_dict is None:
            parameter_dict = {}
        sql_results = []
        for key in result:
            sql_results.append(key)

        sql_params = []
        for key in parameter_dict:
            sql_params.append(key + "=" + parameter_dict[key])
        sql_orders = []
        for key in order_dict:
            sql_orders.append(key + " " + order_dict[key])
        sql = "SELECT "
        if len(sql_results) > 0:
            sql += ",".join(sql_results)
        else:
            sql += "*"
        sql += " FROM " + table_name
        if len(sql_params) > 0:
            sql += " WHERE " + " AND ".join(sql_params)
        if len(sql_orders) > 0:
            sql += " ORDER BY " + ",".join(sql_orders)
        with self.__conn.cursor() as cursor:
            logging.info("Selecting sql: " + sql)
            cursor.execute(sql)
            if num_rows is None:
                rows = cursor.fetchall()
            else:
                rows = cursor.fetchmany(num_rows)
            results = []
            if isinstance(result, dict):
                for row in rows:
                    field_dict = {}
                    i = 0
                    for key in result:
                        field_dict[result[key]] = row[i]
                        i += 1
                    results.append(field_dict)
            elif isinstance(result, list):
                for row in rows:
                    field_dict = {}
                    i = 0
                    for key in result:
                        field_dict[key] = row[i]
                        i += 1
                    results.append(field_dict)
            logging.info("Selected result: " + str(results))
            return results

    def select_column_dict(self, table_name) -> dict:
        """
        查询数据表所有字段信息
        :param table_name:
        :return: 字段与其信息映射dict：{
            'ID': {
                'data_type': 'VARCHAR2',
                'data_length': 32,
                'nullable': False,
                'comment': '主键',
                'is_primary_key': True
            }
        """
        sql = QueryColumns(table_name).format()
        with self.__conn.cursor() as cursor:
            rows = cursor.execute(sql).fetchall()
            results = {}
            for column_name, data_type, data_length, nullable, comment, constraint_name in rows:
                results[column_name] = {
                    'data_type': data_type,
                    'data_length': data_length,
                    'nullable': True if nullable == 'Y' else False,
                    'comment': comment,
                    'is_primary_key': True if constraint_name else False
                }
            return results


class TypeHandler(object):
    """
    类型处理器
    """

    @staticmethod
    def convert_oracle_type(oracle_type, data_length) -> JavaType:
        """
        将Oracle类型转换为Java类型
        """
        if oracle_type == OracleType.CHAR.name or oracle_type == OracleType.VARCHAR2.name:
            return JavaType.String
        if oracle_type == OracleType.NUMBER.name:
            # if data_length > 18:
            #     return JavaType.BigDecimal
            if data_length >= 10:
                return JavaType.Long
            return JavaType.Integer
        if oracle_type == OracleType.DATE.name or oracle_type.startswith(OracleType.TIMESTAMP.name):
            return JavaType.Date
        return JavaType.Object


class OracleType(Enum):
    """
    Oracle类型枚举
    """
    VARCHAR2 = 0
    CHAR = 1
    NUMBER = 10
    DATE = 20
    TIMESTAMP = 21
