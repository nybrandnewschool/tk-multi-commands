'''
This example shows how you can use the app.Panel class to take care of
registering a Panel Widget for your engine. Panels can be saved to a workspace
and restored automatically the next time an app launches. Only certain engines
like tk-nuke and tk-maya support Panels.

This example is in the tk-nuke folder so it will only be available in that
engine.
'''

from sgtk.platform.qt import QtCore, QtGui
from tk_multi_commands import app, engine, context


class SayHelloPanel(app.Panel):

    name = 'Say Hello Panel...'
    properties = {
        'icon': app.get_resource('icons/say_hello.png'),
        'description': 'Greet the current user with a message.',
    }

    def execute(self):
        widget_cls = SayHelloUI
        widget_args = (context.user['name'],)
        widget_kwargs = {}
        return widget_cls, widget_args, widget_kwargs


class SayHelloUI(QtGui.QWidget):

    def __init__(self, user, parent=None):
        super(SayHelloUI, self).__init__(parent)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(QtGui.QLabel(
            f'Hello, <b>{user}</b>!!',
            alignment=QtCore.Qt.AlignCenter,
        ))
        self.setLayout(layout)


def register():
    SayHelloPanel.register()


def unregister():
    pass
