#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
A Dance of Fire and Ice.

@Author Kingen
"""
import time

from pykeyboard import PyKeyboard


class FireAndIce:
    """
    A Dance of Fire and Ice
    """
    keyboard = PyKeyboard()
    START_DEGREE = 1020

    """
    A group of points with regular degrees.
    """
    STRAIGHT = [180]
    LEFT = [90]
    RIGHT = [270]
    LEFT_RIGHT = [90, 270]
    RIGHT_LEFT = [270, 90]
    QUARTER_SPEED = (180, 0.25)
    DOUBLE_SPEED = (180, 2)
    LEFT_RIGHT_3 = [STRAIGHT * 3, LEFT, STRAIGHT * 3, RIGHT]
    RIGHT_LEFT_3 = [STRAIGHT * 3, RIGHT, STRAIGHT * 3, LEFT]

    # data for levels
    # speed: the initial angular speed, degrees/second.
    # points (arguments of each point):
    #   if it's an integer, it represents the degree of angle revolving around the pivot point
    #   if it's a list, it represents a group of points
    #   if it's a tuple, it represents the degree of angle and the change of angular speed against previous one
    LEVEL_DATA = {
        "1-X": {
            "speed": 458.0,
            "points": [
                STRAIGHT * 30, RIGHT_LEFT, STRAIGHT * 14, RIGHT_LEFT, STRAIGHT * 14, RIGHT_LEFT,
                STRAIGHT * 14, LEFT_RIGHT, STRAIGHT * 14, LEFT_RIGHT, STRAIGHT * 12, LEFT_RIGHT * 2,
                STRAIGHT * 8, RIGHT_LEFT * 4, STRAIGHT * 12, LEFT_RIGHT * 2, STRAIGHT * 8,
                RIGHT_LEFT * 2, STRAIGHT * 2, LEFT_RIGHT, QUARTER_SPEED, STRAIGHT * 5
            ]
        }
    }

    def run(self, level: str):
        """
        Starts the specific level.
        """
        data = self.LEVEL_DATA[level]
        # flatten arguments of points
        points = [self.START_DEGREE]
        self.__append_point(points, data['points'])

        speed = data["speed"]
        intervals = [5]
        for point in points:
            if isinstance(point, int):
                degree = point
            elif isinstance(point, tuple):
                degree = point[0]
                speed *= point[1]
            else:
                raise KeyError

            if speed == 0:
                break
            elif speed < 0:
                interval = (360 - degree) / (-speed)
            else:
                interval = degree / speed
            intervals.append(interval)
        print("Open the game window to start")
        for interval in intervals:
            time.sleep(interval)
            self.keyboard.tap_key(self.keyboard.space_key)

    def __append_point(self, points: list, point):
        if isinstance(point, list):
            for p in point:
                self.__append_point(points, p)
        else:
            points.append(point)
