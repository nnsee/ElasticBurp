from javax.swing import SwingUtilities
from java.lang import NullPointerException

import re


def get_project_name(tab):
    m = None
    while m is None:
        try:
            title = SwingUtilities.getWindowAncestor(
                SwingUtilities.getRootPane(tab.getParent())
            ).getTitle()
            m = re.search(" - (.*) - ", title)
        except NullPointerException:
            pass
    try:
        return m.group(1)
    except IndexError:
        return ""
