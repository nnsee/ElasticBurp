from javax.swing import SwingUtilities

import re


def get_project_name(tab):
    title = SwingUtilities.getWindowAncestor(
        SwingUtilities.getRootPane(tab.getParent())
    ).getTitle()
    m = re.search(" - (.*) - ", title)
    try:
        return m.group(1)
    except IndexError:
        return ""
