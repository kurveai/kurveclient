#!/usr/bin/env python

from kurveclient.interaction import (
        list_providers
        )


def test_providers():
    assert isinstance(list_providers(), dict)
