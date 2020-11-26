# Overview
This folder contains commands organized by Engine. These are registered in our custom {config}/core/hooks/context_change.py. This provides a much easier method of adding commands to the Shotgun context_menu for any given engine, bypassing the more complex method of creating a custom Application.

# Add your own commands
To add your own commands, add a python file with a register command that takes engine as an argument. As an example, let's setup a command for tk-maya that prints "Hello!". Put the following code in commands/tk-maya/maya_say_hello.py

```
# -*- coding: utf-8 -*-
from __future__ import print_function

def say_hello():
    print("Hello!")

def register(engine):
    engine.register_command(
        'Say Hello!',
        say_hello,
        {"type": "context_menu", "short_name": "say_hello"},
    )
```
