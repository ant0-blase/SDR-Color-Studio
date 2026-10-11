.PHONY: test install uninstall build-mutter

test:
	bash tests/smoke.sh
install:
	bash install.sh
uninstall:
	bash uninstall.sh
build-mutter:
	bash build-mutter.sh
