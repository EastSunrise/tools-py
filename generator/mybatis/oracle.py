#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@Description 数据库操作模块
@Module oracle

@Author Kingen
@Date 2019/8/27
@Version 1.0
"""

from enum import Enum

import cx_Oracle

from generator.template.live_template import QueryColumns
from generator.util.config import CONFIG, LOGGER
from generator.util.enums import JavaType


class Database(Enum):
    """
    数据库枚举
    """
    KXD = CONFIG.parser['db_kxd']


class OracleHelper:
    """
    访问数据库工具
    """

    def __init__(self, database=Database.KXD):
        self.__user = database.value['user']
        self.__password = database.value['password']
        self.__database = 'MyDB'  # set in the file tnsnames.ora
        self.__connection = cx_Oracle.connect(self.__user, self.__password, "MyDB", encoding='UTF-8')

    def commit(self):
        LOGGER.info("COMMIT.")
        self.__connection.commit()

    def rollback(self):
        LOGGER.info("ROLLBACK.")
        self.__connection.rollback()

    def execute(self, sql, commit=True):
        """
        执行sql
        :param sql: sql语句
        :param commit: 是否提交
        :return: 执行结果
        """
        with self.__connection.cursor() as cursor:
            LOGGER.info("Executing sql: " + sql)
            result = cursor.execute(sql).fetchall()
            LOGGER.info("Executed result: " + str(result))
            if commit:
                self.commit()
            return result

    def transaction(self, *sqls) -> bool:
        """
        将多个sql语句当做事务执行
        :param sqls: sql语句列表
        :return: 是否完成
        """
        if not sqls:
            return False
        for sql in sqls:
            try:
                self.execute(sql, False)
            except cx_Oracle.DatabaseError as error:
                LOGGER.error(error)
                self.rollback()
                return False
        self.commit()
        return True

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
            LOGGER.info("表{}不存在".format(table_name))
            return []
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
        with self.__connection.cursor() as cursor:
            LOGGER.info("Selecting sql: " + sql)
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
            LOGGER.info("Selected result: " + str(results))
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
        sql = QueryColumns().format(table_name)
        rows = self.execute(sql, False)
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
