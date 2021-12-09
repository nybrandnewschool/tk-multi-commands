'''
This example shows how you can use app.Command to create a simple command that
will appear in the ShotGrid menu. This example is in the shared folder meaning
it will be available in all engines.
'''

from tk_multi_commands import app, engine, context


class SayHello(app.Command):

    name = 'Say Hello...'
    properties = {
        'icon': app.get_resource('icons/say_hello.png'),
    }

    def execute(self):
        engine.logger.info('HELLO %s!!!', context.user['name'])


def register():
    SayHello.register()


def unregister():
    pass
