.ONESHELL:
.PHONY: init vista

init:
	git submodule update --init --recursive

vista:
	cd frontend
	npm install
	npm run build

preview:
    cd frontend
    npm run preview