#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Sorting Algorithms.

@Author Kingen
"""


def merge_sort(arr: list):
    if len(arr) <= 1:
        return

    mid_idx = len(arr) // 2
    left = arr[:mid_idx]
    right = arr[mid_idx:]
    merge_sort(left)
    merge_sort(right)

    # 合并两个子数组
    i = j = k = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            arr[k] = left[i]
            i += 1
        else:
            arr[k] = right[j]
            j += 1
        k += 1
    while i < len(left):
        arr[k] = left[i]
        i += 1
        k += 1
    while j < len(right):
        arr[k] = right[j]
        j += 1
        k += 1
