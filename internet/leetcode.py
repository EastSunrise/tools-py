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

log = common.create_logger(__name__)


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
    'Integer': 'java.lang.Integer',
    'List': 'java.util.List',
    'Set': 'java.util.Set',
    'Map': 'java.util.Map',
    'Iterator': 'java.util.Iterator'
}
java_type_default_value = {
    'int': '0',
    'long': '0',
    'double': '0.0',
    'boolean': 'false'
}
JavaType = namedtuple('JavaType', ['name', 'imports', 'default_value'])
JavaClass = namedtuple('JavaClass', ['package_name', 'class_name', 'imports', 'methods'])
JavaMethod = namedtuple('JavaMethod', ['name', 'modifiers', 'return_type', 'parameters', 'body'])
JavaParameter = namedtuple('JavaParameter', ['name', 'type'])
Void = JavaType('void', set(), None)


def parse_java_type(type_node: Type) -> JavaType:
    if type_node is None:
        return Void
    attrs = dict((type_node.attrs[i], type_node.children[i]) for i in range(len(type_node.attrs)))
    if isinstance(type_node, TypeArgument):
        return parse_java_type(attrs['type'])
    name, dimensions = attrs['name'], attrs['dimensions']
    dimensions_suffix = '[]' * len(dimensions)
    imports = set()
    if isinstance(type_node, BasicType):
        if len(dimensions) == 0:
            return JavaType(name, imports, java_type_default_value[name])
        return JavaType(name + dimensions_suffix, imports, 'null')
    if isinstance(type_node, ReferenceType):
        imports.add(java_type_imports[name])
        if attrs['arguments'] is None:
            return JavaType(name + dimensions_suffix, imports, 'null')
        args = []
        for arg in attrs['arguments']:
            arg_type = parse_java_type(arg)
            args.append(arg_type.name)
            imports.update(arg_type.imports)
        return JavaType(f'{name}<{",".join(args)}>' + dimensions_suffix, imports, 'null')
    raise ValueError(f'Unsupported type: {type_node}')


def parse_java_class(question: dict) -> JavaClass:
    fid = int(question['questionFrontendId'])
    package_name = f'p{fid // 100 * 100}'
    snippets = question['codeSnippets']
    if snippets is None:
        return JavaClass(package_name, f'Solution{fid}', set(), [])
    codes = [x for x in snippets if x['langSlug'] == 'java']
    if len(codes) == 0:
        return JavaClass(package_name, f'Solution{fid}', set(), [])

    java_code = codes[0]['code']
    class_node = javalang.parse.parse(java_code).types[0]
    class_name = class_node.name if class_node.name != 'Solution' else f'Solution{fid}'
    imports, methods = set(), []
    for constructor in class_node.constructors:
        parameters = []
        for param in constructor.parameters:
            java_type = parse_java_type(param.type)
            parameters.append(JavaParameter(param.name, java_type))
            imports.update(java_type.imports)
        methods.append(JavaMethod(class_name, constructor.modifiers, None, parameters, None))
    for method in class_node.methods:
        parameters = []
        for param in method.parameters:
            java_type = parse_java_type(param.type)
            parameters.append(JavaParameter(param.name, java_type))
            imports.update(java_type.imports)
        return_type = parse_java_type(method.return_type)
        imports.update(return_type.imports)
        body = '' if return_type == Void else f'return {return_type.default_value};'
        methods.append(JavaMethod(method.name, method.modifiers, return_type, parameters, body))
    return JavaClass(package_name, class_name, imports, methods)


def question_as_java_class(dest_dir, jinja2_template, slug: str, visited: dict, replaced=False):
    if slug in visited:
        return
    question = leetcode.get_problem_detail(slug)
    if question is None:
        raise ValueError(f'Question {slug} not found. Try again later')
    fid = int(question['questionFrontendId'])
    log.info('parse question %d. %s', fid, slug)
    java_class = parse_java_class(question)
    visited[slug] = java_class

    package_path = f'{dest_dir}/{java_class.package_name}'
    class_path = os.path.join(package_path, java_class.class_name + '.java')
    if not replaced and os.path.exists(class_path):
        return

    sqs = []
    for sq in json.loads(question['similarQuestions']):
        sq_slug = sq['titleSlug']
        if sq_slug not in visited:
            question_as_java_class(dest_dir, jinja2_template, sq_slug, visited)
        sqs.append(visited[sq_slug])
    tags = [str(x['slug']).upper().replace('-', '_') for x in question['topicTags']]

    kwargs = {
        'fid': fid,
        'slug': slug,
        'title': question['title'],
        'paid_only': question['isPaidOnly'],
        'difficulty': question['difficulty'].upper(),
        'class': java_class,
        'tags': tags,
        'sqs': sqs,
    }
    java_code = jinja2_template.render(kwargs)
    os.makedirs(package_path, exist_ok=True)
    with open(class_path, 'w') as fp:
        fp.write(java_code)


def read_kwargs() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--slug', type=str, default='', help='specify the title slug of the question')
    parser.add_argument('-d', '--dest-dir', type=str, default='', help='specify the directory of problems')
    parser.add_argument('-r', '--replaced', action='store_true', help='enable replaced mode')
    parser.add_argument('-l', '--log-level', default='debug', help='specify the log level of console')
    return parser.parse_args()


# pyinstaller -n leetcode --add-data templates;templates -F leetcode.py
if __name__ == '__main__':
    args = read_kwargs()
    common.console_handler.setLevel(args.log_level.upper())
    slug = args.slug
    if not slug or slug.strip() == '':
        slug = leetcode.get_today_question()['question']['titleSlug']
    qs_dir = args.dest_dir
    if not qs_dir or qs_dir.strip() == '':
        qs_dir = os.path.join(os.path.dirname(__file__), 'src/main/java/cn/kingen/oj/leetcode/problem')
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
    solution_template = Environment(loader=FileSystemLoader(template_dir)).get_template('solution.java.jinja2')
    question_as_java_class(qs_dir, solution_template, slug, {}, args.replaced)
