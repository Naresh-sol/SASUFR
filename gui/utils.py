"""
Shared UI utilities for Smart Attendance System GUI.
Commonly used helpers to avoid code duplication across windows.
"""

from PyQt5 import QtGui


def create_font(family, size, bold=False):
    """Create a QFont object with the given properties."""
    font = QtGui.QFont()
    font.setFamily(family)
    font.setPointSize(size)
    font.setBold(bold)
    if bold:
        font.setWeight(75)
    return font
