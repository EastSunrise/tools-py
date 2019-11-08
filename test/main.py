#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@Description todo
@Module main

@Author Kingen
@Date 2019/10/31
@Version 1.0
"""


def concatSql(preparing, parameter_str):
    """
    拼接sql，占位符为?
    :param preparing:
    :param parameter_str:
    :return:
    """
    preparing = preparing.replace('?', '%s')
    param_list = parameter_str.split(',')
    params = []
    for param_str in param_list:
        param_str = param_str.strip()
        left_bracket = param_str.find('(')
        param_type = param_str[left_bracket + 1:param_str.find(')')]
        param_value = param_str[0:left_bracket]
        if param_type == 'String':
            params.append('\'' + param_value + '\'')
        elif param_type == 'Timestamp':
            params.append('TO_DATE(\'' + '\')')
        else:
            params.append(param_value)
    return preparing % (tuple(params))


def readStatement(log_path, key, start=1):
    with open(log_path, 'r', encoding='UTF-8') as file:
        while start > 1:
            file.readline()
            start -= 1
        line = file.readline()
        return line[line.find(key) + len(key):].strip()


if __name__ == '__main__':
    sql_path = 'D:/Docs/KXJF/sg-campaign/sg-campaign.service.home_IS_UNDEFINED/logs/sg-campaign-service-sql_2019-11-05.log'
    print(concatSql(readStatement(sql_path, 'Preparing:', 1), readStatement(sql_path, 'Parameters:', 2)))
