#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
LeetCode.

@author: Kingen
"""
import argparse
import json
import os
from collections import namedtuple

import javalang
from javalang.tree import BasicType, ReferenceType, TypeArgument, Type
from jinja2 import FileSystemLoader, Environment

import common
from internet import BaseSite

log = common.get_logger()


class LeetCode(BaseSite):
    def __init__(self):
        super().__init__('https://leetcode.cn/', 'leetcode-cn')

    def list_problems(self):
        query = """
        query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) 
        {
            problemsetQuestionList(
                categorySlug: $categorySlug
                limit: $limit
                skip: $skip
                filters: $filters
            ) {
                hasMore
                total
                questions {
                    acRate
                    difficulty
                    freqBar
                    frontendQuestionId
                    isFavor
                    paidOnly
                    solutionNum
                    status
                    title
                    titleCn
                    titleSlug
                    topicTags {
                        name
                        nameTranslated
                        id
                        slug
                    }
                    extra {
                        hasVideoSolution
                        topCompanyTags {
                            imgUrl
                            slug
                            numSubscribed
                        }
                    }
                }
            }
        }
        """
        skip, limit, total = 0, 100, 1
        questions = []
        while skip < total:
            variables = {"categorySlug": "all-code-essentials", "skip": skip, "limit": limit, "filters": {}}
            params = {"query": query, "variables": variables}
            page = {'skip': skip, 'limit': limit}
            result = self.post_json('/graphql/', query=page, json_data=params)
            data = result['data']['problemsetQuestionList']
            questions.extend(data['questions'])
            skip += limit
            total = data['total']
        return questions

    def get_problem_detail(self, slug: str):
        query = """
        query question($titleSlug: String!) {
            question(titleSlug: $titleSlug) {
                questionId
                questionFrontendId
                title
                titleSlug
                isPaidOnly
                difficulty
                likes
                dislikes
                categoryTitle
                content
                editorType
                mysqlSchemas
                dataSchemas
                translatedTitle
                translatedContent
                codeSnippets {
                    lang
                    langSlug
                    code
                }
                envInfo
                enableRunCode
                hasFrontendPreview
                frontendPreviews
                topicTags {
                    name
                    slug
                    translatedName
                }
                hints
                similarQuestions
            }
        }
        """
        variables = {"titleSlug": slug}
        params = {"query": query, "variables": variables}
        return self.post_json('/graphql/', query=variables, json_data=params, cache=True)['data']['question']

    def get_today_question(self):
        query = """
        query questionOfToday {
            todayRecord {
                date
                userStatus
                question {
                    questionId
                    frontendQuestionId: questionFrontendId
                    difficulty
                    title
                    titleCn: translatedTitle
                    titleSlug
                    paidOnly: isPaidOnly
                    freqBar
                    isFavor
                    acRate
                    status
                    solutionNum
                    hasVideoSolution
                    topicTags {
                        name
                        nameTranslated: translatedName
                        id
                    }
                    extra {
                        topCompanyTags {
                            imgUrl
                            slug
                            numSubscribed
                        }
                    }
                }
                lastSubmission {
                    id
                }
            }
        }
        """
        variables = {}
        params = {"query": query, "variables": variables}
        return self.post_json('/graphql/', query=variables, json_data=params)['data']['todayRecord'][0]


leetcode = LeetCode()
java_type_imports = {
    'Boolean': 'java.lang.Boolean',
    'Byte': 'java.lang.Byte',
    'Short': 'java.lang.Short',
    'Integer': 'java.lang.Integer',
    'Long': 'java.lang.Long',
    'Float': 'java.lang.Float',
    'Double': 'java.lang.Double',
    'Character': 'java.lang.Character',
    'String': 'java.lang.String',
    'List': 'java.util.List',
    'Set': 'java.util.Set',
    'Map': 'java.util.Map',
    'Iterator': 'java.util.Iterator'
}
java_type_default_value = {
    'boolean': 'false',
    'byte': '0',
    'short': '0',
    'int': '0',
    'long': '0',
    'float': '0.0',
    'double': '0.0',
    'char': "' '",
}
JavaType = namedtuple('JavaType', ['name', 'imports', 'default_value'])
JavaClass = namedtuple('JavaClass', ['package', 'class_name', 'imports', 'methods'])
JavaMethod = namedtuple('JavaMethod', ['name', 'modifiers', 'return_type', 'parameters', 'body'])
JavaParameter = namedtuple('JavaParameter', ['name', 'type'])
Void = JavaType('void', set(), None)


def parse_java_type(type_node: Type, support_package: str) -> JavaType:
    if type_node is None:
        return Void
    attrs = dict((type_node.attrs[i], type_node.children[i]) for i in range(len(type_node.attrs)))
    if isinstance(type_node, TypeArgument):
        return parse_java_type(attrs['type'], support_package)
    name, dimensions = attrs['name'], attrs['dimensions']
    dimensions_suffix = '[]' * len(dimensions)
    imports = set()
    if isinstance(type_node, BasicType):
        if len(dimensions) == 0:
            return JavaType(name, imports, java_type_default_value[name])
        return JavaType(name + dimensions_suffix, imports, 'null')
    if isinstance(type_node, ReferenceType):
        if name in java_type_imports:
            imports.add(java_type_imports[name])
        else:
            support_package = support_package.strip()
            if support_package != '' and not support_package.endswith('.'):
                support_package += '.'
            imports.add(support_package + name)
        if attrs['arguments'] is None:
            return JavaType(name + dimensions_suffix, imports, 'null')
        arg_names = []
        for arg in attrs['arguments']:
            arg_type = parse_java_type(arg, support_package)
            arg_names.append(arg_type.name)
            imports.update(arg_type.imports)
        return JavaType(f'{name}<{",".join(arg_names)}>' + dimensions_suffix, imports, 'null')
    raise ValueError(f'Unsupported type: {type_node}')


def parse_class_name(fid: str, class_name: str, qs_package: str):
    qs_package = qs_package.strip()
    if qs_package != '' and not qs_package.endswith('.'):
        qs_package = qs_package + '.'
    try:
        fid = int(fid)
        if class_name == 'Solution':
            return f'{qs_package}p{fid // 100 * 100}', f'Solution{fid}'
        else:
            return f'{qs_package}p{fid // 100 * 100}', class_name
    except ValueError:
        if fid.startswith('面试题'):
            parts = fid[4:].split('.')
            if class_name == 'Solution':
                return f'{qs_package}ch{int(parts[0]):02d}', f'Interview{int(parts[1]):02d}'
            else:
                return f'{qs_package}ch{int(parts[0]):02d}', class_name
        if fid.startswith('LCR') or fid.startswith('LCS') or fid.startswith('LCP'):
            pname = fid[0:3].lower()
            if class_name == 'Solution':
                return qs_package + pname, f'{pname.capitalize()}{int(fid[4:]):03d}'
            else:
                return qs_package + pname, class_name
        raise ValueError(f'Invalid question id: {fid}')


def parse_java_class(question: dict, qs_package: str, support_package: str) -> JavaClass:
    fid = question['questionFrontendId']
    snippets = question['codeSnippets']
    if snippets is None:
        package, class_name = parse_class_name(fid, 'Solution', qs_package)
        return JavaClass(package, class_name, set(), [])
    codes = [x for x in snippets if x['langSlug'] == 'java']
    if len(codes) == 0:
        package, class_name = parse_class_name(fid, 'Solution', qs_package)
        return JavaClass(package, class_name, set(), [])

    class_node = javalang.parse.parse(codes[0]['code']).types[0]
    package, class_name = parse_class_name(fid, class_node.name, qs_package)
    imports, methods = set(), []
    for constructor in class_node.constructors:
        parameters = []
        for param in constructor.parameters:
            java_type = parse_java_type(param.type, support_package)
            parameters.append(JavaParameter(param.name, java_type))
            imports.update(java_type.imports)
        methods.append(JavaMethod(class_name, constructor.modifiers, None, parameters, None))
    for method in class_node.methods:
        parameters = []
        for param in method.parameters:
            java_type = parse_java_type(param.type, support_package)
            parameters.append(JavaParameter(param.name, java_type))
            imports.update(java_type.imports)
        return_type = parse_java_type(method.return_type, support_package)
        imports.update(return_type.imports)
        body = '' if return_type == Void else f'return {return_type.default_value};'
        methods.append(JavaMethod(method.name, method.modifiers, return_type, parameters, body))
    return JavaClass(package, class_name, imports, methods)


def save_question(temp, slug, visited, package_dir: str, root_package: str, replaced=False):
    if slug in visited:
        return
    question = leetcode.get_problem_detail(slug)
    if question is None:
        raise ValueError(f'Question {slug} not found. Try again later')
    fid = question['questionFrontendId']
    log.info('parse question %s. %s', fid, slug)
    root_package = root_package.strip()
    if root_package != '' and not root_package.endswith('.'):
        root_package = root_package + '.'
    qs_package, support_package = root_package + 'problem', root_package + 'support'
    java_class = parse_java_class(question, qs_package, support_package)
    visited[slug] = java_class

    if not package_dir or package_dir.strip() == '':
        package_dir = '.'
    package_path = f'{package_dir}/{java_class.package.replace(".", "/")}'
    class_path = f'{package_path}/{java_class.class_name}.java'
    if not replaced and os.path.exists(class_path):
        return

    sqs = []
    for sq in json.loads(question['similarQuestions']):
        sq_slug = sq['titleSlug']
        if sq_slug not in visited:
            save_question(temp, sq_slug, visited, package_dir, root_package, replaced)
        sqs.append(visited[sq_slug])
    tags = [str(x['slug']).upper().replace('-', '_') for x in question['topicTags']]

    kwargs = {
        'fid': fid,
        'slug': slug,
        'title': question['title'],
        'paid_only': question['isPaidOnly'],
        'difficulty': question['difficulty'].upper(),
        'support_package': support_package,
        'class': java_class,
        'tags': tags,
        'sqs': sqs,
    }
    java_code = temp.render(kwargs)
    os.makedirs(package_path, exist_ok=True)
    log.info('write to %s', class_path)
    with open(class_path, 'w', encoding='utf-8') as fp:
        fp.write(java_code)


def read_kwargs() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--slug', type=str, help='specify the title slug of the question')
    parser.add_argument('-d', '--dest-dir', default='src/main/java', help='specify the directory of problems')
    parser.add_argument('-p', '--package', default='leetcode', help='specify the pacakge of problems')
    parser.add_argument('-r', '--replaced', action='store_true', help='enable replaced mode')
    parser.add_argument('-l', '--log-level', default='debug', help='specify the log level of console')
    return parser.parse_args()


# pyinstaller -n leetcode -i ./assets/leetcode.ico --add-data templates;templates -F leetcode.py
if __name__ == '__main__':
    args = read_kwargs()
    common.console_handler.setLevel(args.log_level.upper())
    title_slug = args.slug
    if not title_slug or title_slug.strip() == '':
        title_slug = leetcode.get_today_question()['question']['titleSlug']
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
    solution_template = Environment(loader=FileSystemLoader(template_dir)).get_template('solution.java.jinja2')
    save_question(solution_template, title_slug, {}, args.dest_dir, args.package, args.replaced)
