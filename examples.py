#!/usr/bin/python3 -i
# This file just sets up a few convenient example instances of Enums to play
# with in an interpreter shell..

import errno
from enum import *


# A basic non-valued enum:
class Color (Enum):
    RED = __
    GREEN, BLUE = __ * 2
    RUBY = RED
    EGGPLANT = __(doc="That's a fruit, not a color!")


# This is an example of adding to an Enum class dynamically at runtime:
class Errno (IntEnum):
    pass

for value, name in errno.errorcode.items():
    setattr(Errno, name, value)


# Another IntEnum which has some of the same values as Errno (but they are not
# the same as the Errno constants)
class Align (IntEnum):
    TOP = 1
    BOTTOM = 2
    LEFT = 3
    RIGHT = 4
    UP = TOP
    DOWN = BOTTOM
    SIDEWAYS = __(10, doc="This is an odd one")


# Technically, we don't have to be constrained to ints...
class Shade (TypeEnum, basetype=float):
    BLACK = 0.0
    DARKGRAY = 0.25
    GRAY = 0.5
    LIGHTGRAY = 0.75
    WHITE = 1.0

class Greeting (TypeEnum, basetype=str):
    HELLO = "Hello"
    HI = "Hi"
    YODAWG = "Yo, dawg!"

# Enums are hashable, and can be used as dictionary keys.  Even different enums
# with the same underlying value can be used as different keys (because they do
# not compare equal)
msgs = {Errno.EPERM: "Permission denied", Align.TOP: "Upward ho!"}
