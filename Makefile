# Sreon — build system.   make app    builds build/Sreon.app (macOS)
#                          make test   runs the engine tests (any OS)
#                          make dmg    builds build/Sreon.dmg
CC      ?= cc
UNAME_S := $(shell uname -s)
SRCS    := $(wildcard compiler/src/*.c)
CFLAGS  := -std=c11 -Icompiler/include -O2 -DNDEBUG -w -fno-strict-aliasing
LDFLAGS := -lm
ifeq ($(UNAME_S),Darwin)
  CFLAGS  += -DSPRFST_MACOS=1
  LDFLAGS += -framework CoreFoundation
else
  CFLAGS  += -D_GNU_SOURCE -pthread
  LDFLAGS += -pthread
endif

.PHONY: all app dmg test embed clean icons
all: build/bin/sprfst

build/bin/sprfst: $(SRCS) $(wildcard compiler/include/sprfst/*.h)
	@mkdir -p build/bin
	$(CC) $(CFLAGS) $(SRCS) -o $@ $(LDFLAGS)

embed: build/bin/sprfst
	build/bin/sprfst run tools/embed.spf

test: build/bin/sprfst
	tools/test.sh build/bin/sprfst

app:
	tools/build_app.sh

dmg:
	tools/build_app.sh --dmg

icons:
	python3 tools/make_icons.py

clean:
	rm -rf build
