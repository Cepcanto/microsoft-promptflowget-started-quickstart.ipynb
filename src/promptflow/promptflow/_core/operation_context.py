# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# ---------------------------------------------------------
import os
from contextvars import ContextVar
from typing import Dict

from promptflow._sdk._constants import USER_AGENT
from promptflow._version import VERSION


class OperationContext(Dict):
    """The OperationContext class.

    This class is used to store the context information for the current operation. It is a dictionary-like class
    that can be used to store any primitive context information. The object is a context variable that can be
    accessed from anywhere in the current context. The context information is used to provide additional information
    to the service for logging and telemetry purposes.
    """

    _CONTEXT_KEY = "operation_context"
    _current_context = ContextVar(_CONTEXT_KEY, default=None)

    @classmethod
    def get_instance(cls):
        """Get the OperationContext instance.

        This method returns the OperationContext instance from the current context.
        If there is no instance in the current context, it creates a new one and sets it in the current context.

        Returns:
            OperationContext: The OperationContext instance.
        """
        # get the OperationContext instance from the current context
        instance = cls._current_context.get()
        if instance is None:
            # create a new instance and set it in the current context
            instance = OperationContext()
            cls._current_context.set(instance)
        return instance

    def __setattr__(self, name, value):
        """Set the attribute.

        This method sets an attribute with the given name and value in the OperationContext instance.
        The name must be a string and the value must be a primitive.

        Args:
            name (str): The name of the attribute.
            value (int, float, str, bool, or None): The value of the attribute.

        Raises:
            TypeError: If name is not a string or value is not a primitive.
        """
        # check that name is a string
        if not isinstance(name, str):
            raise TypeError("Name must be a string")
        # check that value is a primitive
        if value is not None and not isinstance(value, (int, float, str, bool)):
            raise TypeError("Value must be a primitive")
        # set the item in the data attribute
        self[name] = value

    def __getattr__(self, name):
        """Get the attribute.

        This method returns the attribute with the given name from the OperationContext instance.
        If there is no such attribute, it returns the default attribute from the super class.

        Args:
            name (str): The name of the attribute.

        Returns:
            int, float, str, bool, or None: The value of the attribute.
        """
        if name in self:
            return self[name]
        else:
            super().__getattribute__(name)

    def __delattr__(self, name):
        """Delete the attribute.

        This method deletes the attribute with the given name from the OperationContext instance.
        If there is no such attribute, it deletes the default attribute from the super class.

        Args:
            name (str): The name of the attribute.
        """
        if name in self:
            del self[name]
        else:
            super().__delattr__(name)

    def get_user_agent(self):
        """Get the user agent string.

        This method returns the user agent string for the OperationContext instance.
        The user agent string consists of the promptflow-sdk version and any additional user agent information stored in
        the user_agent attribute.

        Returns:
            str: The user agent string.
        """

        def parts():
            agent = self.get("user_agent", '')
            yield agent
            promptflow_agent = f"promptflow/{VERSION}"
            yield promptflow_agent if promptflow_agent not in agent else ''
            user_agent = os.environ.get(USER_AGENT, '').strip()
            yield user_agent if user_agent not in agent else ''

        return " ".join(parts()).strip()

    def append_user_agent(self, user_agent: str):
        """Append the user agent string.

        This method appends user agent information to the user_agent attribute of the OperationContext instance.
        If there is no user_agent attribute, it creates one with the given user agent information.

        Args:
            user_agent (str): The user agent information to append.
        """
        agent = self.get("user_agent", '')
        user_agent = user_agent.strip()
        if user_agent not in agent:
            self.user_agent = f"{agent} {user_agent}".strip()

    def get_context_dict(self):
        """Get the context dictionary.

        This method returns the context dictionary for the OperationContext instance.
        The context dictionary is a dictionary that contains all the context information stored in the OperationContext
        instance.

        Returns:
            dict: The context dictionary.
        """
        return dict(self)
