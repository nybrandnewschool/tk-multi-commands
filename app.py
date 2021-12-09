# -*- coding: utf-8 -*-

# Standard library imports
import os
import types
import sys

# Third party imports
from sgtk.platform import Application


def normalize(*parts):
    path = os.path.normpath(os.path.expanduser(os.path.join(*parts)))
    return path.replace('\\', '/')


class MultiCommandsApp(Application):
    """
    This application provides a simple method of registering commands with
    a Shotgun Engine when it is initialized.

    Rather than requiring you to create a new app to register commands,
    tk-multi-commands will lookup python modules to register in it's commands
    path. By default the commands path will include `{config}/commands` and
    any paths you add to the env var `SHOTGUN_MULTI_COMMANDS_PATH`. It may be
    useful to add a shared network path to `SHOTGUN_MULTI_COMMANDS_PATH` to
    allow adding commands to Shotgun without having to modify your pipeline
    configuration.

    A commands directory is organized by engine and can also include a shared
    directory to load for all engines. You may include any additonal resources
    like icons in the commands directory as well.

    Example commands directory:
        {commands_dir}/tk-maya/my_maya_commands.py
        {commands_dir}/shared/my_shared_commands.py

    Each python module should contain a register function. This will be called
    after loading the module and allows you to register commands with the
    engine instance or perform any other setup. You can check the context
    object to make your commands context sensitive.

    A special virtual module, `tk_multi_commands`, is available in command
    modules and provides a simple way of obtaining the correct app, engine,
    and context objects.

    For example:
        from tk_multi_commands import app, engine, context

    See also:
        You can find additional examples in the examples/ folder and README.md.

    """

    def init_app(self):
        """
        Setup commands path and prepare Application for registering commands.
        """

        class Command(object):
            """
            Class for creating declarative commands in command modules.
            """

            name = 'Command'
            properties = {}

            def __init__(self, app, engine, context):
                self.app = app
                self.engine = engine
                self.context = context
                self.properties = dict(self.properties)

                # Resolve icon in commands_path
                if 'icon' in self.properties:
                    icon = self.properties['icon']
                    if not os.path.isfile(icon):
                        self.properties['icon'] = app.get_resource(icon)

            @classmethod
            def register(cls):
                cmd = cls(self, self.engine, self.context)
                self.engine.register_command(
                    name=cmd.name,
                    callback=cmd.execute,
                    properties=cmd.properties,
                )

            def execute(self, *args, **kwargs):
                """
                Subclasses must implement this method.
                """

        # A convenience class for creating declarative commands in command
        # modules.
        self.Command = Command

        # This is a virtual module used to grab the app, engine, and context
        # in command modules.
        self.tk_multi_commands = types.ModuleType(name='tk_multi_commands')
        self.tk_multi_commands.__file__ = __file__
        self.tk_multi_commands.app = self
        self.tk_multi_commands.engine = self.engine
        self.tk_multi_commands.context = self.context

        # Load all command modules!
        self.commands_path = self._load_commands_path()
        self.commands_registry = []
        self.commands_modules = self._load_commands()

    def destroy_app(self):
        """
        Remove tk_multi_commands from sys.modules and delete it
        making sure we don't leak tk_multi_commands beyond the scope of
        the current context.
        """

        # Destroy tk_multi_commands
        module = self.__dict__.pop('tk_multi_commands', None)
        if module:
            sys.modules.pop(module.__name__, None)
        del(module)

        # Unload all command modules in the registry
        self._unload_commands(self.commands_modules)
        self.commands_modules[:] = []
        self.commands_registry[:] = []

    def get_resource(self, path):
        """
        Attempts to resolve a file path relative to the commands_path.

        Arguments:
            path (str): Path for lookup like "icons/my_icon.png"
        """

        for command_path in self.commands_path:
            potential_path = normalize(command_path, path)
            if os.path.exists(potential_path):
                return potential_path

    @property
    def context_change_allowed(self):
        return True

    def post_context_change(self, old_context, new_context):
        for obj in self.commands_modules + self.commands_registry:
            obj.app = self
            obj.engine = self.engine
            obj.logger = self.logger
            obj.context = new_context

            if hasattr(obj, 'context_changed'):
                obj.context_changed(old_context, new_context)

    def _load_commands_path(self):
        """
        Load commands path.
        """

        commands_path = []

        # Add paths from environment variable
        env_path = os.getenv('SHOTGUN_MULTI_COMMANDS_PATH')
        if env_path:
            commands_path += [
                normalize(path)
                for path in env_path.split(os.pathsep)
            ]

        # Add paths from pipeline configuration
        config_path = normalize(
            self.engine.sgtk.pipeline_configuration.get_config_location(),
            'commands',
        )
        commands_path.append(config_path)

        return commands_path

    def _load_commands(self):
        """
        Load python modules found in the commands path.
        """

        commands = []

        for command_path in self.commands_path:

            engine_path = normalize(command_path, self.engine.instance_name)
            shared_path = normalize(command_path, 'shared')
            for path in (engine_path, shared_path):

                if not os.path.isdir(path):
                    continue

                self.logger.debug('Loading commands in "%s"', path)

                for file in os.listdir(path):
                    if not file.endswith('.py'):
                        continue

                    module_file = normalize(path, file)
                    try:
                        module = self._import_module(module_file)
                        if hasattr(module, 'register'):
                            module.register()
                        self.logger.debug(
                            'Loaded command module "%s"',
                            module_file
                        )
                        commands.append(module)
                    except Exception:
                        self.logger.exception(
                            'Failed to load command module "%s"',
                            module_file,
                        )

        return commands

    def _import_module(self, module_file):
        """
        Compile a python file and return a Module.
        """

        # Prepare module object
        module = types.ModuleType(name=os.path.basename(module_file)[:-3])
        module.__file__ = module_file
        sys.modules[self.tk_multi_commands.__name__] = self.tk_multi_commands

        try:
            # Add to sys.modules to ensure sys.module[__name__] works inside
            # the modules code.
            sys.modules[module.__name__] = module

            # Compile code object
            code = compile(open(module_file, 'r').read(), module_file, 'exec')

            # Execute code in module namespace
            exec(code, module.__dict__, module.__dict__)
            return module

        finally:
            # Pop module from sys.modules so we don't interfere with standard
            # imports.
            sys.modules.pop(module.__name__)

    def _unload_commands(self, commands):
        """
        Calls the unregister function in each command module.
        """

        for command in self.commands_modules:
            try:
                if hasattr(command, 'unregister'):
                    command.unregister()
                self.logger.debug(
                    'Unloaded command module "%s"',
                    command.__file__
                )
            except Exception:
                self.logger.exception(
                    'Failed to unload command module "%s"',
                    command.__file__,
                )
