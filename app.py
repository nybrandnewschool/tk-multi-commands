# -*- coding: utf-8 -*-

# Standard library imports
import os
import types
import sys
from abc import ABCMeta, abstractmethod
from contextlib import contextmanager

# Third party imports
from sgtk.platform import Application

# compatible with Python 2 *and* 3:
ABC = ABCMeta('ABC', (object,), {'__slots__': ()})


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

        class Command(ABC):
            """
            Baseclass used to declare ShotGrid Commands.

            Required Attributes:
                name (str): The name of the command in Menus.
                properties (dict): Command properties: icon, description,
                    short_name, title, group, group_default, type like
                    "context_menu", "panel", or "node".

            See Also:
                https://developer.shotgridsoftware.com/tk-core/platform.html#sgtk.platform.Engine.register_command
            """

            @property
            @abstractmethod
            def name(self):
                return 'Command'

            @property
            @abstractmethod
            def properties(self):
                return {}

            def __init__(self, app, engine, context):
                self.app = app
                self.engine = engine
                self.context = context
                self.properties = dict(self.properties)
                self.logger = app.logger

            @classmethod
            def register(cls):
                # "self" here is the MultiCommandsApp instance.
                cmd = cls(self, self.engine, self.context)

                # Check availability
                if not cmd.available():
                    return

                cmd.init()
                with ApplicationProxy(self, self.engine, cmd):
                    self.engine.register_command(
                        name=cmd.name,
                        callback=cmd.execute,
                        properties=cmd.properties,
                    )

                self.commands_registry.append(cmd)

            def show_dialog(self, title, widget, *args, **kwargs):
                return self.engine.show_dialog(
                    title,
                    self.app,
                    widget,
                    *args,
                    **kwargs
                )

            def show_modal(self, title, widget, *args, **kwargs):
                return self.engine.show_modal(
                    title,
                    self.app,
                    widget,
                    *args,
                    **kwargs
                )

            def available(self):
                """Return True if the Command is available for the current
                app, context, and engine.
                """
                return True

            def init(self):
                """Perform additional setup before the Command is registered."""
                return NotImplemented

            def context_changed(self, old_context, new_context):
                """Subclasses can use this to respond to context changes."""
                return NotImplemented

            @abstractmethod
            def execute(self):
                """The callback that will be called when this Command is run by
                ShotGrid.
                """
                return NotImplemented

        class Panel(ABC):
            """
            Baseclass used to declare ShotGrid Panel UIs.

            Attributes:
                name (str): The name of the command in Menus.
                properties (dict): Command properties: icon, description,
                    short_name, title, group, group_default, type like
                    "context_menu", "panel", or "node".

            See Also:
                https://developer.shotgridsoftware.com/tk-core/platform.html#sgtk.platform.Engine.register_panel
            """

            @property
            @abstractmethod
            def name(self):
                return 'Command'

            @property
            @abstractmethod
            def properties(self):
                return {}

            def __init__(self, app, engine, context):
                self.app = app
                self.engine = engine
                self.context = context
                self.properties = dict(self.properties, **{'type': 'panel'})
                self.logger = app.logger

                # Store panel id and widget
                self.id = None
                self.widget = None

            @classmethod
            def register(cls):
                # "self" here is the MultiCommandsApp instance.
                cmd = cls(self, self.engine, self.context)

                # Check availability
                if not cmd.available():
                    return

                cmd.init()

                # Register panel
                with ApplicationProxy(self, self.engine, cmd):
                    cmd.id = self.engine.register_panel(cmd.show_panel)
                    self.engine.register_command(
                        name=cmd.name,
                        callback=cmd.show_panel,
                        properties=cmd.properties,
                    )

                self.commands_registry.append(cmd)

            def show_panel(self):
                widget_cls, widget_args, widget_kwargs = self.execute()
                widget = self.engine.show_panel(
                    self.id,
                    self.properties.get('title', self.name),
                    self.app,
                    widget_cls,
                    *widget_args,
                    **widget_kwargs
                )
                self.widget = widget
                self.add_closeEvent(widget)
                return widget

            def add_closeEvent(self, widget):
                widget._panel = self
                widget._old_closeEvent = getattr(widget, 'closeEvent', None)

                def closeEvent(self, event):
                    self._panel.logger.debug('Closing %s', self)
                    self._panel._on_close(self)
                    if self._old_closeEvent:
                        self._old_closeEvent(event)

                widget.closeEvent = closeEvent

            def _on_close(self, widget):
                self.logger.debug('_on_close %s', widget)
                if widget == self.widget:
                    self.logger.debug('Clearing widget instance on %s.', self)
                    self.widget = None

                self.on_close(widget)

            def on_close(self, widget):
                """Called when the Panels widget is closed."""
                return

            def available(self):
                """Return True if the Command is available for the current
                app, context, and engine.
                """
                return True

            def init(self):
                """Perform additional setup before the Command is registered."""
                return NotImplemented

            def context_changed(self, old_context, new_context):
                """Called after a Context is changed."""
                return NotImplemented

            @abstractmethod
            def execute(self):
                """
                The callback used by app.register_panel and app.show_panel.
                Must return a tuple (QWidget class, args, kwargs). The args and
                kwargs will be passed to the QWidget class during construction.
                """
                return NotImplemented

        @contextmanager
        def ApplicationProxy(app, engine, cmd):
            """Replace Application object with Proxy in context."""

            class _ApplicationProxy(object):

                @property
                def display_name(self):
                    if isinstance(cmd, app.Command):
                        default_display_name = 'Commands'
                    elif isinstance(cmd, app.Panel):
                        default_display_name = 'Panels'
                    else:
                        default_display_name = app.display_name
                    return cmd.properties.get(
                        'group',
                        default_display_name,
                    )

                def __eq__(self, other):
                    return (
                        app == other or
                        self.display_name == getattr(other, 'display_name', '')
                    )

                def __getattr__(self, attr):
                    return getattr(app, attr)

            _real_app = engine._Engine__currently_initializing_app or app
            _proxy_app = _ApplicationProxy()
            try:
                engine._Engine__currently_initializing_app = _proxy_app
                yield _proxy_app
            finally:
                engine._Engine__currently_initializing_app = _real_app

        # A convenience class for creating declarative commands in command
        # modules.
        self.Command = Command
        self.Panel = Panel

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
        """
        Call the context_changed callback on all registered Commands and
        Command modules.
        """

        # Execute Command context_changed callbacks
        for obj in self.commands_modules + self.commands_registry:
            obj.app = self
            obj.engine = self.engine
            obj.logger = self.logger
            obj.context = new_context

            if hasattr(obj, 'context_changed'):
                obj.context_changed(old_context, new_context)

        # Ensure Commands get added back to Engine!
        # The default implementation in engine.__load_apps uses "is" to find
        # commands belonging to apps. That check failied with the
        # ApplicationProxy tk-multi-commands uses to allow submenu grouping.
        command_pool = self.engine._Engine__command_pool
        commands = self.engine._Engine__commands
        for command_name, command in command_pool.items():
            command_app = command.get('properties', dict()).get('app')
            if command_app == self:
                commands[command_name] = command

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
