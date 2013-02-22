# Name:   enum.py
# Author: Alex Stewart <foogod@gmail.com>
# Date:   Feb 2, 2013
#
# Note: This is a quick reference implementation of some ideas from a
# discussion on the python-ideas maillist.  It is fairly full-featured, but not
# complete or well tested yet, and probably needs some tweaking and sorting out
# of corner-cases.
#
# This module is not recommended for general use.

__all__ = ['Enum', 'TypeEnum', 'IntEnum']

KWARG_ATTR_MAP = {'doc': '__doc__'}


class EnumStub:
    def __init__(self, basetype=None, value=None, name=None, kwargs={}):
        self._name = name
        self._basetype = basetype
        self._value = value
        self._kwargs = kwargs

    @property
    def _args(self):
        if self._basetype is None:
            return (self._name,)
        else:
            return (self._name, self._value)


class PlaceholderStub (EnumStub):
    def __call__(self, value=None, **kwargs):
        if self._basetype is None:
            if value is not None:
                raise TypeError("Cannot set a value for this type of enum")
            stub = PlaceholderStub(kwargs=kwargs)
        else:
            if value is None:
                raise TypeError("Must set a value for this type of enum")
            value = self._basetype(value)
            stub = TypeEnumStub(self._basetype, value, kwargs=kwargs)
        return stub

    def __mul__(self, count):
        return (self.__class__(kwargs=self._kwargs) for x in range(count))

    def __rmul__(self, count):
        return self.__mul__(count)


class TypeEnumStub (EnumStub):
    def __getattribute__(self, attr):
        if attr not in ('_name', '_basetype', '_value', '_args', '_kwargs'):
            return getattr(self._value, attr)
        return object.__getattribute__(self, attr)

    def __setattr__(self, attr, value):
        if attr not in ('_name', '_basetype', '_value', '_args', '_kwargs'):
            return setattr(self._value, attr, value)
        return object.__setattr__(self, attr, value)


class EnumSetupDict (dict):
    def __init__(self, basetype=None):
        self.basetype = basetype

    def __getitem__(self, item):
        if item == '__':
            return PlaceholderStub(self.basetype)
        return dict.__getitem__(self, item)

    def __setitem__(self, item, value):
        # Note: TypeEnumStubs will appear to be instances of the basetype due
        # to the fact that they mimic all attributes of their _value, so we
        # need to make sure to check for the stub case first.
        if isinstance(value, EnumStub):
            if isinstance(value, PlaceholderStub) and self.basetype:
                raise TypeError("Must set a value for this type of enum")
            if not value._name:
                value._name = item
        elif self.basetype and isinstance(value, self.basetype):
            value = TypeEnumStub(self.basetype, value, item)
        return dict.__setitem__(self, item, value)


class EnumType (type):
    @classmethod
    def __prepare__(meta, name, bases):
        return EnumSetupDict()

    def __new__(meta, name, bases, classdict):
        cls = type.__new__(meta, name, bases, dict(classdict))
        stubs = {}
        for attr, value in sorted(classdict.items()):
            if isinstance(value, EnumStub):
                if not value._name:
                    value._name = attr
                if value not in stubs:
                    delattr(cls, attr)
                    stubs[value] = cls.new(*value._args, **value._kwargs)
                if value._name != attr:
                    setattr(cls, attr, stubs[value])
        return cls

    def __str__(cls):
        return "{}.{}".format(cls.__module__, cls.__name__)

    def __repr__(cls):
        return "<enum class: {}.{}>".format(cls.__module__, cls.__name__)

    def new(cls, name, **kwargs):
        if cls.get(name) is not None:
            raise ValueError("Duplicate enum name: {!r}".format(name))
        elif hasattr(cls, name):
            raise ValueError("Invalid enum name: {!r}".format(name))
        self = object.__new__(cls)
        for k, v in kwargs.items():
            setattr(self, KWARG_ATTR_MAP.get(k, k), v)
        self.name = name
        setattr(cls, name, self)
        return self

    def get(cls, item, default=None):
        if isinstance(item, str):
            result = getattr(cls, item, None)
            if isinstance(result, Enum) and issubclass(cls, result.__class__):
                return result
        return default

    def get_value(cls, value, default=None):
        return cls.get(value, default)

    def __getitem__(cls, item):
        result = cls.get(item)
        if result is None:
            raise KeyError(item)
        return result

    def __contains__(cls, item):
        return cls.get(item) is not None

    def __iter__(cls):
        found = set()
        for c in cls.__mro__:
            if issubclass(type(c), EnumType):
                for attr, value in c.__dict__.items():
                    if attr not in found:
                        found.add(attr)
                        if isinstance(value, c) and value.name == attr:
                            yield value


class Enum (metaclass=EnumType):
    def __new__(cls, value):
        result = cls.get_value(value)
        if result is None:
            raise ValueError("No equivalent {} value: {!r}".format(cls, value))
        return result

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<{}.{}>".format(self.__class__, self.name)


class TypeEnumType (EnumType):
    @classmethod
    def __prepare__(meta, name, bases, **kwargs):
        if 'basetype' in kwargs:
            basetype = kwargs['basetype']
            if basetype is None:
                # This is an "abstract" class.  Don't do the magic enum
                # processing.
                return dict()
        else:
            for b in bases:
                if isinstance(b, TypeEnumType):
                    basetype = b.basetype
                    if basetype is not None:
                        break
            else:
                raise TypeError("basetype not specified for TypeEnum subclass")
        return EnumSetupDict(basetype)

    def __new__(meta, name, bases, classdict, **kwargs):
        basetype = getattr(classdict, 'basetype', None)
        if basetype is not None:
            if basetype not in bases:
                bases = bases + (basetype,)
        classdict['basetype'] = basetype
        classdict['_value_map'] = {}
        cls = EnumType.__new__(meta, name, bases, classdict)
        return cls

    def __init__(meta, name, bases, classdict, **kwargs):
        EnumType.__init__(meta, name, bases, classdict)

    def __setattr__(cls, attr, value):
        if isinstance(value, cls):
            cls._value_map.setdefault(value.value, attr)
        elif isinstance(value, cls.basetype):
            return cls.new(attr, value)
        return EnumType.__setattr__(cls, attr, value)

    def __delattr__(cls, attr):
        prev = getattr(cls, attr, None)
        if isinstance(prev, cls):
            if cls._value_map.get(prev.value) is attr:
                # We're deleting a previous enum, so remove it from the
                # reverse-mapping dict as well.
                del cls._value_map[prev.value]
        return EnumType.__delattr__(cls, attr)

    def new(cls, name, value, **kwargs):
        basetype = cls.basetype
        if basetype is None:
            basetype = object
        self = basetype.__new__(cls, value)
        prev = cls.get(name)
        if prev is not None:
            if prev.value == self.value:
                return prev
            else:
                raise ValueError("Duplicate enum name: {!r}".format(name))
        elif hasattr(cls, name):
            raise ValueError("Invalid enum name: {!r}".format(name))
        elif cls.get_value(self) is not None:
            raise ValueError("Duplicate enum value: {!r}".format(value))
        for k, v in kwargs.items():
            setattr(self, KWARG_ATTR_MAP.get(k, k), v)
        self.name = name
        setattr(cls, name, self)
        return self

    def get_value(cls, value, default=None):
        for c in cls.__mro__:
            if issubclass(c, TypeEnum):
                name = c._value_map.get(value)
                if name:
                    return cls.get(name, default)
        return default


class TypeEnum (Enum, metaclass=TypeEnumType, basetype=None):
    def __repr__(self):
        return "<{}.{} ({!r})>".format(self.__class__, self.name, self.value)

    #TODO: implement other comparison operators
    def __eq__(self, other):
        if isinstance(other, Enum) and other is not self:
            return False
        return self.basetype.__eq__(self, other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.value)

    @property
    def value(self):
        return self.basetype(self)


class IntEnum (TypeEnum, basetype=int):
    pass
