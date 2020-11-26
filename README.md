# tk-multi-commands
A Shotgun Toolkit application that dynamically loads commands from a configurable list of directories.

# Commands Path
The `commands_path` is the list of paths the app will load commands from. Each path should be a directory containing python files organized by engine. Each python file should contain a `register` function which will be called when tk-multi-commands is initialized. The `register` functions will be passed, `app`, `engine`, and `context`.

The `commands_path` contains a commands directory in your pipeline configuration as well as paths provided by the `SHOTGUN_MULTI_COMMANDS_PATH` environment variable.

## Commands directory structure
```
commands/
    {engine}/
        {command_module}.py
    shared/
        command_module.py
```

## Example command module
Let's imagine you want to add a custom command to the tk-aftereffects engine. Create a file in commands/tk-afterffects called say_hello.py with the following contents.

```
from tk_multi_command import app, engine, context


class SayHello(app.Command):

    name = 'Say Hello...'
    icon = app.get_resource('icons/say_hello.png')

    def execute(self):
        engine.logger.info('HELLO %s!!!', context.user['name'])


def register():
    SayHello.register()


def unregister():
    pass
```

At the top of the file we import the `app, engine, and context` from the `tk_multi_command`. This is a special import only available in command modules and provides a simple way for you to access the correct `app, engine, and context` objects. Then we derive our SayHello class from `app.Command` which is a convenience way of defining Shotgun commands in a more declarative fashion. Finally we register our SayHello command in the module level register function. You can register as many commands as you like here or perform some other setup you require.

# Installation
Make the changes in the example_config directory to your own shotgun pipeline configuration.
