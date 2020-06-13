#   Copyright 2020 The KNIX Authors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

SHELL := /bin/bash

VERSION?=$(shell git describe --tags)
PKG=mfn_cli-$(VERSION)-py3-none-any.whl

default: dist/$(PKG)

clean:
	rm -rf build/ dist/ mfn_cli.egg-info/ mfn_cli/__pycache__/

dist/$(PKG): mfn_cli/*.py setup.cfg setup.py
	rm -f $(PKG)
	sed 's/^__version__ .*$$/__version__ = "$(VERSION)"/' -i mfn_cli/__init__.py
	sed 's/mfn_sdk >= "auto"$$/mfn_sdk >= "$(VERSION)"/' -i setup.cfg
	python3 setup.py sdist bdist_wheel
	sed 's/^__version__ .*$$/__version__ = "auto"/' -i mfn_cli/__init__.py
	sed 's/mfn_sdk >= "$(VERSION)"$$/mfn_sdk >= "auto"/' -i setup.cfg

dist: dist/$(PKG)
