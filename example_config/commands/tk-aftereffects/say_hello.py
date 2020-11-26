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
