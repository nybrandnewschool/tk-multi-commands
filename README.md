# tk-multi-commands
A Shotgun Toolkit application that dynamically loads commands from a configurable list of directories.

# Commands Path
The `commands_path` is the list of paths the app will load commands from. Each path should be a directory containing python files organized by engine. Each python file should contain a `register` function which will be called when tk-multi-commands is initialized.

The `commands_path` contains a commands directory in your pipeline configuration as well as paths provided by the `SHOTGUN_MULTI_COMMANDS_PATH` environment variable.

## Commands Directory Structure
Below `{engine}` refers to the engine instance_name like *tk-maya* or *tk-nuke*. Command modules in the `shared` folder will be available for all engines.
```
commands/
    {engine}/
        command_module.py
    shared/
        command_module.py
```

## Example Command
Let's imagine you want to add a custom command to the tk-aftereffects engine. Create a file in commands/tk-afterffects called say_hello.py with the following contents.

```
from tk_multi_commands import app, engine, context


class SayHello(app.Command):

    name = 'Say Hello...'
    # Properties to pass to register_command
    # See also: https://developer.shotgridsoftware.com/tk-core/platform.html#sgtk.platform.Engine.register_command
    properties = {
        'icon': app.get_resource('icons/say_hello.png'),
        'description': 'Greet the current user with a message.',
    }

    def execute(self):
        engine.logger.info('HELLO %s!!!', context.user['name'])


def register():
    SayHello.register()


def unregister():
    pass
```

At the top of the file we import the `app, engine, and context` from the `tk_multi_commands`. This is a special import only available in command modules and provides a simple way for you to access the correct `app, engine, and context` objects. Then we derive our SayHello class from `app.Command`. Finally we register our SayHello Command in a module level register function. You can register as many commands as you like here or perform some other setup you require.

## Example Panel
You can also register Panel UIs which appear docked in supported applications like Maya and Nuke. Let's convert the previous Command into a simple Panel.

```
import json
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

    def context_changed(self, old_context, new_context):
        user = new_context.user['name']
        ctx = json.dumps(new_context.to_dict(), indent=4)
        self.logger.debug(f'Updating {self.widget}...')
        self.widget.label.setText(f'The context has changed, <b>{user}</b>!!')
        self.widget.context.setText(f'<pre>{ctx}</pre>')


class SayHelloUI(QtGui.QWidget):

    def __init__(self, user, parent=None):
        super(SayHelloUI, self).__init__(parent)

        self.label = QtGui.QLabel(
            f'Hello, <b>{user}</b>!!',
            alignment=QtCore.Qt.AlignCenter,
        )
        self.context = QtGui.QLabel()
        layout = QtGui.QVBoxLayout()
        layout.setRowStretch(1, 1)
        layout.addWidget(self.label)
        layout.addWidget(self.context)
        self.setLayout(layout)


def register():
    SayHelloPanel.register()


def unregister():
    pass
```

As in the Command example, we must implement the `execute` method. However, the execute method on a Panel must return a QWidget class and arguments to pass to it. We also implement the `context_changed` method so we can update the UI when the context changes.

## API
### Command Module Basics
Command modules may subclass app.Command and app.Panel and register their subclasses in a module level `register` function. Command modules may also include an `unregister` function which can be used to perform cleanup.
```
from tk_multi_commands import app, context, engine

class MyCommand(app.Command):
    ...

def register():
    MyCommand.register()

def unregister():
    ...
```


### *class* app.Command
```
Baseclass used to declare ShotGrid Commands.


Required Attributes:
    name (str): The name of the Command in ShotGrid context menus.
    properties (dict): Command properties: icon, description, short_name,
    title, group, group_default, type like "context_menu", "panel", or "node".

    See also:
        https://developer.shotgridsoftware.com/tk-core/platform.html#sgtk.platform.Engine.register_command.

Instance Attributes:
    app (MultiCommandsApp) - The parent application instance.
    context (sgtk.context.Context) - The current Context.
    engine (sgtk.engine.Engine) - The current Engine like tk-maya, tk-nuke...

Required Methods:
    def execute(self):
        The callback that will be called when this Command is run by ShotGrid.

Optional Methods:
    def available(self):
        Return True if the Command is available for the current
        app, context, and engine.

    def init(self):
        Perform additional setup before the Command is registered.

    def context_changed(self, old_context, new_context):
        Called after a Context is changed.
```

### *class* app.Panel
```
Baseclass used to declare ShotGrid Panel UIs.

Required Attributes:
    name (str): The name of the Command in ShotGrid context menus.
    properties (dict): Command properties: icon, description, short_name,
    title, group, group_default, type like "context_menu", "panel", or "node".

    See also:
        https://developer.shotgridsoftware.com/tk-core/platform.html#sgtk.platform.Engine.register_panel.

Instance Attributes:
    app (MultiCommandsApp) - The parent application instance.
    context (sgtk.context.Context) - The current Context.
    engine (sgtk.engine.Engine) - The current Engine like tk-maya, tk-nuke...

Required Methods:
    def execute(self):
        The callback used by app.register_panel and app.show_panel. Must return
        a tuple (QWidget class, args, kwargs). The args and kwargs will be
        passed to the QWidget class during construction.

Optional Methods:
    def available(self):
        Return True if the Command is available for the current
        app, context, and engine.

    def init(self):
        Perform additional setup before the Command is registered.

    def context_changed(self, old_context, new_context):
        Called after a Context is changed.
```

# Installation
Make the changes in the example_config directory to your own ShotGrid pipeline configuration.
