#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
LeetCode.

@author: Kingen
"""

from internet import BaseSite


class LeetCode(BaseSite):
    def __init__(self):
        super().__init__('https://leetcode.cn/', 'leetcode-cn')

    def list_problems(self):
        query = """
        query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
            problemsetQuestionList(categorySlug: $categorySlug   limit: $limit   skip: $skip  filters: $filters) {
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
            result = self.post_json('/graphql/', query=page, json_data=params, cache=skip + limit < total)
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
